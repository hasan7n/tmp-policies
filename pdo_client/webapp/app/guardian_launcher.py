"""Launch a guardian container for an asset.

The owner's "deploy behind a guardian" action shells out to guardian/run.sh,
which starts the guardian via ``docker run``. run.sh blocks for the lifetime of
the container, so it is launched as a detached background process; the asset
card is updated with the guardian's host/port immediately (see
``views.assets.AssetDeployGuardianEndpoint``).
"""

import logging
import os
import subprocess

from django.conf import settings

logger = logging.getLogger(__name__)


def deploy_guardian(data_path):
    """Start a guardian container serving ``data_path`` (a host file).

    The guardian is published on ``GUARDIAN_PORT`` at ``F_SERVICE_HOST`` (the
    service host the webapp is configured with) and bound on all interfaces.
    Returns ``(guardian_url, guardian_port)`` — the host/port to record on the
    asset — after spawning run.sh; it does not wait for the container to be
    ready.
    """
    run_script = os.path.join(settings.GUARDIAN_DIR, "run.sh")
    if not os.path.isfile(run_script):
        raise FileNotFoundError(f"guardian run script not found: {run_script}")

    guardian_host = settings.F_SERVICE_HOST
    port = str(settings.GUARDIAN_PORT)

    cmd = [
        "bash",
        run_script,
        "--image", settings.GUARDIAN_IMAGE,
        "--interface", "0.0.0.0",
        "--port", port,
        "--sservice-port", str(settings.GUARDIAN_SSERVICE_PORT),
        "--guardian-host", guardian_host,
        "--data-path", data_path,
    ]

    log_path = os.path.join(settings.SCRATCH_DIR, "guardian_run.log")
    logger.info("Launching guardian: %s (log: %s)", " ".join(cmd), log_path)
    log_file = open(log_path, "ab")
    # Detach into its own session so the container outlives the request; run.sh
    # blocks for the container lifetime, so we deliberately do not wait on it.
    subprocess.Popen(
        cmd,
        cwd=settings.GUARDIAN_DIR,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    return guardian_host, port
