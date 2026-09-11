#!/usr/bin/env bash
#
# Bring the whole stack up the way a Codespace does, then drive the inference
# tutorial through a browser and record it.
#
# This is the same sequence as .devcontainer/start.sh -- ledger, enclave
# services, registries, FL server, webapp -- with the test on the end. Kept
# separate from that file because a codespace stops where a reader takes over,
# and this does not.
#
# Usage: bash tools/tests/run_webui_inference_test.sh [options]
#
#   -p PORT     port to serve the webapp on (default 8000)
#   -k          keep the stack running after the test (default: tear it down)
#   -n          do not rebuild the environment; drive whatever is already up
#   -H          run headed (needs a DISPLAY); records nothing
#   -a DIR      artifacts directory (default /tmp/pdo_webui_artifacts)

set -eEuo pipefail

PORT=8000
KEEP=""
NO_SETUP=""
HEADED=""
ARTIFACTS=/tmp/pdo_webui_artifacts

while getopts "p:knHa:h" opt; do
    case "$opt" in
        p) PORT="$OPTARG" ;;
        k) KEEP=1 ;;
        n) NO_SETUP=1 ;;
        H) HEADED="--headed" ;;
        a) ARTIFACTS="$OPTARG" ;;
        h) sed -n '2,20p' "$0"; exit 0 ;;
        *) exit 1 ;;
    esac
done

TESTS="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# The docker_*.sh orchestration scripts invoke their per-service helpers by
# relative path, so they have to run from the tools/ directory that holds them.
TOOLS="$( cd "$TESTS/.." && pwd )"
PYTHON="${PYTHON:-python3}"

cd "$TOOLS"
mkdir -p "$ARTIFACTS"

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

teardown() {
    # Called twice: once up front to clear a previous run, where -k does not
    # apply, and once from the EXIT trap, where it does.
    if [ -z "${1:-}" ] && [ -n "$KEEP" ]; then
        echo "Leaving the stack up (-k)."
        return
    fi
    echo "==> Stopping everything this run started"
    # The recorder's ffmpeg is a child of the test process, so a test killed by
    # a signal leaves it running and still writing to run.mp4. A second run then
    # has two writers on one file and produces a video that will not decode --
    # which looks like a broken recorder rather than a stale process.
    pkill -f "x11grab.*${ARTIFACTS}" >/dev/null 2>&1 || true
    bash "$TOOLS/stop_all.sh" >/dev/null 2>&1 || true
    pkill -f "docker_start_webapp.sh" >/dev/null 2>&1 || true
    pkill -f "pdo_client/docker/run_webapp.sh" >/dev/null 2>&1 || true
    pkill -f "policy_engine/run_ledger.sh" >/dev/null 2>&1 || true
    pkill -f "policy_engine/run_services.sh" >/dev/null 2>&1 || true
    # Inference guardians are named per port (one per dataset), so they are
    # cleared by image rather than by a single name; stop_all.sh does that. The
    # rest have fixed names.
    docker rm -f policies_web_client pdo-guardian \
        services_container ccf_container \
        asset_registry_container template_registry_container >/dev/null 2>&1 || true
    docker ps -aq --filter "name=pdo-inference-guardian" \
        | xargs -r docker rm -f >/dev/null 2>&1 || true
    bash "$TOOLS/docker_stop_all.sh" >/dev/null 2>&1 || true
}
trap teardown EXIT

if [ -z "$NO_SETUP" ]; then
    # A half-torn-down previous run is the most common reason a fresh one fails
    # in a way that looks like a code problem, so start from nothing.
    echo "==> Clearing anything left from a previous run"
    teardown force
    sleep 3
    # A failure screenshot from a previous run left sitting here would be read as
    # this run's -- the recipe says screenshots mean the run failed.
    rm -f "$ARTIFACTS"/*.png "$ARTIFACTS"/*.html \
          "$ARTIFACTS/run.mp4" "$ARTIFACTS/run_4x.mp4" 2>/dev/null || true
    # The waits below are for files. Left in place by a previous run they are
    # satisfied instantly, and everything downstream then starts against a
    # policy engine that is not up yet.
    rm -rf /tmp/pdo_ledger /tmp/pdo_services 2>/dev/null || {
        echo "Cannot clear /tmp/pdo_ledger or /tmp/pdo_services -- a container" >&2
        echo "created part of them as root. Remove them with sudo and retry." >&2
        exit 1
    }

    echo "==> Generating user keys"
    bash docker_generate_user_keys.sh

    echo "==> Starting the policy engine (ledger + services)"
    nohup bash docker_start_policy_engine.sh > /tmp/pdo_engine.log 2>&1 &

    echo "==> Waiting for the ledger"
    wait_for "the ledger" 600 test -f /tmp/pdo_ledger/ccf/keys/networkcert.pem

    echo "==> Waiting for the enclave services"
    wait_for "the enclave services" 900 test -f /tmp/pdo_services/services/etc/site.toml

    echo "==> Starting the asset and template registries"
    nohup bash docker_start_registries.sh > /tmp/pdo_registries.log 2>&1 &
    HOST_IP="$(hostname -I | awk '{print $1}')"
    wait_for "the asset registry" 180 curl -sf "http://$HOST_IP:8001/api/assets/"
    wait_for "the template registry" 180 curl -sf "http://$HOST_IP:8002/api/policies/"

    echo "==> Creating the tutorial files"
    bash make_tutorial_files.sh

    echo "==> Starting the FL server"
    nohup bash start_fl_server.sh > /tmp/pdo_fl_server.log 2>&1 &
    wait_for "the FL server" 60 curl -sf http://localhost:7920/info

    # Fail loudly rather than driving whatever else is already answering there.
    if curl -s -o /dev/null --max-time 3 "http://127.0.0.1:${PORT}/"; then
        echo "Something is already listening on 127.0.0.1:${PORT}; pass -p to pick another port." >&2
        exit 1
    fi

    echo "==> Starting the webapp (with the guardian deploy watcher)"
    WEBAPP_PORT="$PORT" nohup bash docker_start_webapp.sh > /tmp/pdo_webapp.log 2>&1 &
    wait_for "the webapp" 300 curl -sf "http://127.0.0.1:${PORT}/"
fi

echo "==> Driving the tutorial"
set +e
(
    cd "$TESTS"
    "$PYTHON" webui_inference_test.py \
        --port "$PORT" --artifacts "$ARTIFACTS" $HEADED
)
STATUS=$?
set -e

# The recording is real time, which is more than most people want to sit
# through. Leave a 4x copy beside it; the original stays authoritative.
VIDEO="$ARTIFACTS/run.mp4"
if [ -s "$VIDEO" ]; then
    FFMPEG="$(command -v ffmpeg || "$PYTHON" -c \
        'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())' 2>/dev/null)"
    if [ -n "$FFMPEG" ]; then
        "$FFMPEG" -y -loglevel error -i "$VIDEO" \
            -filter:v setpts=PTS/4 -an "$ARTIFACTS/run_4x.mp4" || true
    fi
    "${FFMPEG:-true}" -hide_banner -i "$VIDEO" 2>&1 | grep -E 'Duration' || true
fi

echo
echo "artifacts: $ARTIFACTS"
echo "logs:      /tmp/pdo_engine.log /tmp/pdo_registries.log /tmp/pdo_fl_server.log /tmp/pdo_webapp.log"
echo "           $TOOLS/pdo_scratch/guardian_requests/guardian_deploy.log"
exit $STATUS
