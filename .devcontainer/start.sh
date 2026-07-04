#!/usr/bin/env bash
#
# Codespaces startup: bring up the whole PDO stack and the webapp, then print the
# URL to open. Run automatically by the devcontainer's postStartCommand; safe to
# re-run (it skips startup when the webapp is already running).
#
# It does NOT run the demo seed — the tutorial creates everything by hand.

set -euo pipefail

REPO="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$REPO"

# Already up? nothing to do.
if docker ps --format '{{.Names}}' 2>/dev/null | grep -q '^policies_web_client$'; then
    echo "PDO webapp already running — open the forwarded port 8000."
    exit 0
fi

echo "==> Waiting for the Docker daemon"
until docker info >/dev/null 2>&1; do sleep 1; done

INTERFACE="$(hostname -I | awk '{print $1}')"

# Pull the images up front so the timed waits in the start scripts below are
# meaningful (otherwise the first `docker run` would also be pulling).
echo "==> Pulling images (first run only; this can take a few minutes)"
for img in \
    mlcommons/pdo_ledger:latest \
    mlcommons/pdo_services:latest \
    mlcommons/pdo_base_client:latest \
    mlcommons/pdo_toy_asset_registry:latest \
    mlcommons/pdo_toy_template_registry:latest \
    mlcommons/toy_guardian:latest ; do
    docker pull "$img"
done

echo "==> Generating user keys"
bash docker_generate_user_keys.sh

echo "==> Starting the policy engine (ledger + services)"
bash docker_start_policy_engine.sh

echo "==> Starting the asset and template registries"
bash docker_start_registries.sh
sleep 5

echo "==> Creating the tutorial data file at /tmp/asset_data.txt"
echo "The eagle lands at midnight." > /tmp/asset_data.txt

echo "==> Starting the webapp (with the guardian deploy watcher)"
export CSRF_TRUSTED_ORIGINS="https://*.app.github.dev,https://*.githubpreview.dev"
nohup bash docker_start_webapp.sh > /tmp/pdo_webapp.log 2>&1 &

cat <<EOF

============================================================
 PDO WebUI is starting on port 8000.
 Open the forwarded URL for port 8000 (see the "Ports" tab),
 then follow pdo_client/webapp/TUTORIAL.md.

 Webapp logs:   /tmp/pdo_webapp.log
 Guardian logs: $REPO/pdo_client/pdo_scratch/guardian_requests/guardian_deploy.log
============================================================
EOF
