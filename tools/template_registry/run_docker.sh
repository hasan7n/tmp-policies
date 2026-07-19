TEMPLATE_REGISTRY_IMAGE=""
INTERFACE=""
PORT=""

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Run the template_registry container.

Options:
  -i, --image IMAGE        Docker image to run (required)
  -n, --interface IFACE    Host interface to publish (required)
  -p, --port PORT          Host port to publish (required)
  -h, --help               Show this help and exit
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        -i|--image)     TEMPLATE_REGISTRY_IMAGE="$2"; shift 2 ;;
        -n|--interface) INTERFACE="$2"; shift 2 ;;
        -p|--port)      PORT="$2"; shift 2 ;;
        -h|--help)      usage; exit 0 ;;
        *)              echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

# Required arguments
[ -n "$TEMPLATE_REGISTRY_IMAGE" ] || { echo "Missing required option: -i/--image" >&2; usage >&2; exit 1; }
[ -n "$INTERFACE" ]               || { echo "Missing required option: -n/--interface" >&2; usage >&2; exit 1; }
[ -n "$PORT" ]                    || { echo "Missing required option: -p/--port" >&2; usage >&2; exit 1; }

docker run --rm --user "$(id -u):0" --name template_registry_container \
    -p $INTERFACE:$PORT:8000 $TEMPLATE_REGISTRY_IMAGE
