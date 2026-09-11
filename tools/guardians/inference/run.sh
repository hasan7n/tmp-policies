GUARDIAN_IMAGE=""
INTERFACE=""
PORT=""
SSERVICE_PORT=""
GUARDIAN_HOST=""
DATA_PATH=""
FL_SERVER_URL=""
# Defaults to the container hostname inside the image, which is fine for a lone
# guardian and wrong as soon as there are two: a job carries a capability minted
# for one guardian, so the FL server needs a name to address that job to.
FL_CLIENT_ID=""

# Where the host data file is mounted inside the container; the guardian core
# reads it via the GUARDIAN_DATA_PATH env var (see guardian_core/inference.py).
CONTAINER_DATA_PATH="/project/guardian_data"

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Run the inference guardian container: the guardian core (which processes
do_inference capabilities) and the FL client that redeems them, together.

Options:
  -i, --image IMAGE        Docker image to run (required)
  -n, --interface IFACE    Host interface to publish (required)
  -p, --port PORT          Host port to publish (required)
  -s, --sservice-port PORT Host storage-service port to publish (required)
  -g, --guardian-host URL  Guardian Host (required)
  -d, --data-path PATH     Host data file to serve (required). Mounted into the
                           container and exposed as GUARDIAN_DATA_PATH.
  -f, --fl-server-url URL  FL server the bundled client polls for jobs (required)
  -c, --fl-client-id ID    Name the bundled client claims jobs under; whoever
                           submits a job for this guardian addresses it to this
                           name (default: the container hostname)
  -h, --help               Show this help and exit
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        -i|--image)         GUARDIAN_IMAGE="$2"; shift 2 ;;
        -n|--interface)     INTERFACE="$2"; shift 2 ;;
        -p|--port)          PORT="$2"; shift 2 ;;
        -s|--sservice-port) SSERVICE_PORT="$2"; shift 2 ;;
        -g|--guardian-host) GUARDIAN_HOST="$2"; shift 2 ;;
        -d|--data-path)     DATA_PATH="$2"; shift 2 ;;
        -f|--fl-server-url) FL_SERVER_URL="$2"; shift 2 ;;
        -c|--fl-client-id)  FL_CLIENT_ID="$2"; shift 2 ;;
        -h|--help)          usage; exit 0 ;;
        *)                  echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

# Required arguments
[ -n "$GUARDIAN_IMAGE" ] || { echo "Missing required option: -i/--image" >&2; usage >&2; exit 1; }
[ -n "$INTERFACE" ]      || { echo "Missing required option: -n/--interface" >&2; usage >&2; exit 1; }
[ -n "$PORT" ]           || { echo "Missing required option: -p/--port" >&2; usage >&2; exit 1; }
[ -n "$SSERVICE_PORT" ]  || { echo "Missing required option: -s/--sservice-port" >&2; usage >&2; exit 1; }
[ -n "$GUARDIAN_HOST" ]  || { echo "Missing required option: -g/--guardian-host" >&2; usage >&2; exit 1; }
[ -n "$DATA_PATH" ]      || { echo "Missing required option: -d/--data-path" >&2; usage >&2; exit 1; }
[ -n "$FL_SERVER_URL" ]  || { echo "Missing required option: -f/--fl-server-url" >&2; usage >&2; exit 1; }

# One container per port, so redeploying onto a port replaces what was there while
# a guardian on another port -- another dataset, another policy -- keeps running.
CONTAINER_NAME="pdo-inference-guardian-${PORT}"
docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true

# --add-host lets the bundled FL client reach an FL server published on the host
# when the URL names host.docker.internal.
docker run --rm --env F_GUARDIAN_HOST=$GUARDIAN_HOST --env INTERFACE=0.0.0.0 --user "$(id -u):0" \
    --add-host host.docker.internal:host-gateway \
    -v "${DATA_PATH}:${CONTAINER_DATA_PATH}:ro" \
    --env "GUARDIAN_DATA_PATH=${CONTAINER_DATA_PATH}" \
    --env "FL_SERVER_URL=${FL_SERVER_URL}" \
    --env "FL_CLIENT_ID=${FL_CLIENT_ID}" \
    -p $INTERFACE:$PORT:7900 -p $INTERFACE:$SSERVICE_PORT:7901 \
    --name "$CONTAINER_NAME" $GUARDIAN_IMAGE
