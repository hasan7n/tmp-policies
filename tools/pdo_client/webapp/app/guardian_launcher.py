"""Start a guardian container for an asset.

Registering an asset also deploys a guardian for it. How the guardian is started
depends on where the webapp runs:

* Not containerized (``CONTAINERIZED_DEPLOYMENT`` off): the webapp has Docker
  access and runs the guardian command itself as a detached subprocess.
* Containerized (``CONTAINERIZED_DEPLOYMENT`` on): the webapp has no Docker
  access, so it writes the command as a shell script into ``GUARDIAN_DEPLOY_DIR``
  (a directory shared with the host); the host-side launcher watches that
  directory and runs each script.

Either way, ``run.sh`` owns the actual ``docker run`` invocation, so it is not
duplicated here. After deploying, poll ``wait_until_healthy`` until the
guardian's ``/info`` endpoint responds.
"""

import logging
import os
import subprocess
import time

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def guardian_run_command(data_path):
    """Return ``(command, guardian_host, guardian_port)``.

    ``command`` is a ``guardian/run.sh`` invocation that starts the guardian
    serving ``data_path``, published on ``GUARDIAN_PORT`` at ``F_SERVICE_HOST``
    (the service host the webapp is configured with) and bound on all
    interfaces.
    """
    guardian_host = settings.F_SERVICE_HOST
    port = str(settings.GUARDIAN_PORT)
    sservice_port = str(settings.GUARDIAN_SSERVICE_PORT)
    run_script = os.path.join(settings.GUARDIAN_DIR, "run.sh")

    command = " \\\n".join(
        [
            f"bash {run_script}",
            f"    --image {settings.GUARDIAN_IMAGE}",
            "    --interface 0.0.0.0",
            f"    --port {port}",
            f"    --sservice-port {sservice_port}",
            f"    --guardian-host {guardian_host}",
            f"    --data-path {data_path}",
        ]
    )
    return command, guardian_host, port


def deploy_guardian(data_path):
    """Start a guardian serving ``data_path`` and return ``(host, port)``.

    Dispatches on ``CONTAINERIZED_DEPLOYMENT`` (see module docstring). Does not
    wait for the guardian to be ready — call ``wait_until_healthy`` for that.
    """
    command, host, port = guardian_run_command(data_path)

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

    run.sh blocks for the container lifetime, so it is deliberately not waited
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
