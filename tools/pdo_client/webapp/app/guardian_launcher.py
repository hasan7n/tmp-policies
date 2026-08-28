"""Start a guardian for an asset.

Registering an asset also deploys a guardian for it. The owner chooses which kind,
where it listens (``settings.SERVE_ON_CHOICES``), and on which port. Each kind owns
a ``run.sh`` and a manifest saying which options that script takes (see
``app.guardian_registry``), so this module never names a guardian: it computes the
values a launch could need and lets each manifest pick the ones it wants.

How the resulting command is executed depends on where the webapp runs:

* Not containerized (``CONTAINERIZED_DEPLOYMENT`` off): the webapp has Docker
  access and runs the guardian command itself as a detached subprocess.
* Containerized (``CONTAINERIZED_DEPLOYMENT`` on): the webapp has no Docker
  access, so it writes the command as a shell script into ``GUARDIAN_DEPLOY_DIR``
  (a directory shared with the host); the host-side launcher watches that
  directory and runs each script.

Either way, each ``run.sh`` owns the actual invocation, so it is not duplicated
here. After deploying, poll ``wait_until_healthy`` until the guardian's ``/info``
endpoint responds — every guardian answers it.
"""

import logging
import os
import socket
import subprocess
import time

import requests
from django.conf import settings

from . import guardian_registry

logger = logging.getLogger(__name__)


def resolve_serve_on(serve_on):
    """Map a ``serve_on`` choice to ``(bind_interface, advertised_host)``.

    ``bind_interface`` is what the guardian listens on; ``advertised_host`` is the
    host recorded on the asset and burned into the token contract, so it must be
    an address the requester and the policy author can actually reach.
    """
    if serve_on == "localhost":
        return "127.0.0.1", "localhost"
    if serve_on == "0.0.0.0":
        return "0.0.0.0", settings.F_SERVICE_HOST
    if serve_on == "HOSTNAME":
        return "0.0.0.0", socket.gethostname()
    raise ValueError(f"unknown serve_on: {serve_on!r}")


def _storage_port(port):
    """The PDO storage service port that pairs with a guardian on ``port``.

    Derived rather than configured so two guardians on different ports do not
    collide on one shared storage port. Guardians that need no storage service
    simply never ask for this value.
    """
    return int(port) + 1


def launch_values(manifest, data_path, *, serve_on, port):
    """Everything a launch could need, for a manifest to draw the parts it takes.

    The keys are ``guardian_registry.LAUNCH_VALUES``; a manifest that names one
    outside that set is rejected when it is loaded, so anything reachable here is
    known to exist.
    """
    bind_interface, advertised_host = resolve_serve_on(serve_on)
    return {
        "data_path": data_path,
        "bind_interface": bind_interface,
        "advertised_host": advertised_host,
        "port": str(port),
        "storage_port": str(_storage_port(port)),
        "image": manifest.image,
        "fl_server_url": settings.FL_SERVER_URL_FROM_GUARDIAN,
    }


def guardian_run_command(data_path, *, guardian_type, serve_on, port):
    """Return ``(command, advertised_host, port)`` for one guardian.

    ``command`` is the ``run.sh`` invocation that starts a guardian of
    ``guardian_type`` serving ``data_path``, with exactly the options its manifest
    declares, in the order it declares them.
    """
    manifest = guardian_registry.get(guardian_type)
    values = launch_values(manifest, data_path, serve_on=serve_on, port=port)

    parts = [f"bash {manifest.run_script}"]
    for option, value_name in manifest.options.items():
        parts.append(f"    {option} {values[value_name]}")

    return " \\\n".join(parts), values["advertised_host"], values["port"]


def deploy_guardian(data_path, *, guardian_type, serve_on, port):
    """Start a guardian serving ``data_path`` and return ``(host, port)``.

    Dispatches on ``CONTAINERIZED_DEPLOYMENT`` (see module docstring). Does not
    wait for the guardian to be ready — call ``wait_until_healthy`` for that.
    """
    command, host, port = guardian_run_command(
        data_path, guardian_type=guardian_type, serve_on=serve_on, port=port
    )

    if settings.CONTAINERIZED_DEPLOYMENT:
        _write_deploy_request(command)
    else:
        _run_command(command)

    return host, port


def _write_deploy_request(command):
    """Drop the guardian command into GUARDIAN_DEPLOY_DIR for the host watcher.

    Written atomically (temp file + rename) so the watcher never reads a
    half-written script.
    """
    deploy_dir = settings.GUARDIAN_DEPLOY_DIR
    os.makedirs(deploy_dir, exist_ok=True)
    name = f"guardian_{os.urandom(6).hex()}.sh"
    final_path = os.path.join(deploy_dir, name)
    tmp_path = final_path + ".tmp"
    with open(tmp_path, "w") as f:
        f.write("#!/usr/bin/env bash\n" + command + "\n")
    os.rename(tmp_path, final_path)
    logger.info("Wrote guardian deploy request: %s", final_path)


def _run_command(command):
    """Run the guardian command as a detached background process.

    run.sh blocks for the guardian's lifetime, so it is deliberately not waited
    on; readiness is confirmed separately via wait_until_healthy.
    """
    log_path = os.path.join(settings.SCRATCH_DIR, "guardian_run.log")
    logger.info("Running guardian command (log: %s)", log_path)
    log_file = open(log_path, "ab")
    subprocess.Popen(
        ["bash", "-c", command],
        stdout=log_file,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )


def wait_until_healthy(host, port, timeout=120, interval=3):
    """Poll the guardian's ``/info`` until it responds 200, or raise.

    A 200 from ``/info`` means the guardian service is listening and ready.
    Raises ``TimeoutError`` if the guardian is not healthy within ``timeout``
    seconds.
    """
    url = f"http://{host}:{port}/info"
    deadline = time.monotonic() + timeout
    last_error = None
    while time.monotonic() < deadline:
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                logger.info("Guardian healthy at %s", url)
                return
            last_error = f"HTTP {resp.status_code}"
        except requests.RequestException as e:
            last_error = str(e)
        time.sleep(interval)
    raise TimeoutError(
        f"Guardian did not become healthy at {url} within {timeout}s "
        f"(last error: {last_error})"
    )
