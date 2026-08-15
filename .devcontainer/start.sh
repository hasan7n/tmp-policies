#!/usr/bin/env bash
#
# Codespaces startup: bring up the whole PDO stack and the webapp, then print the
# URL to open. Run automatically by the devcontainer's postStartCommand; safe to
# re-run (it skips startup when the webapp is already running).
#
# It does NOT run the demo seed — the tutorial creates everything by hand.

set -eEuo pipefail

REPO="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
# The docker_*.sh orchestration scripts below invoke their per-service helpers by
# relative path, so they have to run from the tools/ directory that holds them.
TOOLS="$REPO/tools"
cd "$TOOLS"

# Where the Docker daemon keeps its images, and roughly the room the stack's
# images need there.
DOCKER_ROOT=/var/lib/docker
[ -d "$DOCKER_ROOT" ] || DOCKER_ROOT=/
REQUIRED_GB=14

# Report a failure and stop, but leave the codespace created: a non-zero exit
# from the postStartCommand aborts container creation altogether and hands the
# user a bare recovery container, with none of this workspace to debug from.
abort() {
    cat >&2 <<EOF

============================================================
 STARTUP FAILED: $*

$(df -h "$DOCKER_ROOT" | sed 's/^/ /')

 Re-run once the cause is fixed:  bash .devcontainer/start.sh
============================================================
EOF
    exit 0
}
trap 'abort "command failed: $BASH_COMMAND"' ERR

# Poll a command until it succeeds, giving up after a deadline so a service that
# never comes up fails the startup instead of hanging it forever.
wait_for() {
    local description="$1" timeout="$2"
    shift 2
    local deadline=$(( SECONDS + timeout ))
    until "$@" >/dev/null 2>&1; do
        if [ "$SECONDS" -ge "$deadline" ]; then
            echo "Timed out after ${timeout}s waiting for $description" >&2
            return 1
        fi
        sleep 2
    done
}

# Already up? nothing to do.
if docker ps --format '{{.Names}}' 2>/dev/null | grep -q '^policies_web_client$'; then
    echo "PDO webapp already running — open the forwarded port 8000."
    exit 0
fi

echo "==> Waiting for the Docker daemon"
wait_for "the Docker daemon" 300 docker info

# Filling the disk partway through a pull reports only "no space left on device"
# against an unnamed layer, so measure the room the images need before starting.
available_gb=$(df -BG --output=avail "$DOCKER_ROOT" | tail -n 1 | tr -dc '0-9')
if [ "$available_gb" -lt "$REQUIRED_GB" ]; then
    abort "only ${available_gb}GB free under $DOCKER_ROOT, and the images need about ${REQUIRED_GB}GB. Reclaim space with 'docker system prune -a', or recreate the codespace on a machine type with a larger disk."
fi

# Pull the images up front so the timed waits in the start scripts below are
# meaningful (otherwise the first `docker run` would also be pulling). One image
# at a time: concurrent pulls keep every compressed download and every unpacked
# layer on disk simultaneously, which needs far more room than the images do.
echo "==> Pulling images (first run only; this can take a few minutes)"
for img in \
    mlcommons/pdo_ledger:latest \
    mlcommons/pdo_services:latest \
    mlcommons/pdo_base_client:latest \
    mlcommons/pdo_toy_asset_registry:latest \
    mlcommons/pdo_toy_template_registry:latest \
    mlcommons/toy_guardian:latest ; do
    echo "    $img"
    docker pull --quiet "$img" >/dev/null || abort "could not pull $img"
done

echo "==> Generating user keys"
bash docker_generate_user_keys.sh

echo "==> Starting the policy engine (ledger + services)"
bash docker_start_policy_engine.sh

# The services container writes site.toml once every enclave service is
# registered; the webapp needs that file to configure its PDO client.
echo "==> Waiting for the enclave services"
wait_for "the enclave services" 600 test -f /tmp/pdo_services/services/etc/site.toml

echo "==> Starting the asset and template registries"
bash docker_start_registries.sh
wait_for "the asset registry" 120 curl -s "http://127.0.0.1:8001/"
wait_for "the template registry" 120 curl -s "http://127.0.0.1:8002/"

echo "==> Creating the tutorial data file at /tmp/asset_data.txt"
echo "The eagle lands at midnight." > /tmp/asset_data.txt

echo "==> Starting the webapp (with the guardian deploy watcher)"
export CSRF_TRUSTED_ORIGINS="https://*.app.github.dev,https://*.githubpreview.dev"
nohup bash docker_start_webapp.sh > /tmp/pdo_webapp.log 2>&1 &

# The webapp registers its contracts on the ledger before it serves anything, so
# give it room. A codespace is still usable if this times out — the logs named
# in the banner say why — so report it rather than failing the startup.
echo "==> Waiting for the WebUI to answer on port 8000"
if wait_for "the WebUI on port 8000" 900 curl -s "http://127.0.0.1:8000/"; then
    STATUS="PDO WebUI is up on port 8000."
else
    STATUS="PDO WebUI has not answered yet — check the webapp log below."
fi

cat <<EOF

============================================================
 $STATUS
 Open the forwarded URL for port 8000 (see the "Ports" tab),
 then follow the tutorial.

 Webapp logs:   /tmp/pdo_webapp.log
 Guardian logs: $TOOLS/pdo_scratch/guardian_requests/guardian_deploy.log
 Data file:     /tmp/asset_data.txt
============================================================
EOF
