"""Build the command that starts a guardian container for an asset.

The webapp may itself run inside a container with no access to the Docker
daemon, so rather than launching the guardian it hands the owner a ready-to-run
``guardian/run.sh`` command to run on the guardian host (see
``views.assets.AssetDeployGuardianEndpoint``). run.sh owns the actual
``docker run`` invocation, so it is not duplicated here.
"""

import os

from django.conf import settings


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
