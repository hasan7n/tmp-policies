TEMPLATE_REGISTRY_IMAGE="mlcommons/pdo_toy_template_registry:latest"
HOST_BIND="$(hostname -I | awk '{print $1}'):8002"

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Run the template_registry container.

Options:
  -i, --image IMAGE        Docker image to run (default: $TEMPLATE_REGISTRY_IMAGE)
  -b, --bind IFACE:PORT    Host interface:port to publish (default: $HOST_BIND)
  -h, --help               Show this help and exit
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        -i|--image) TEMPLATE_REGISTRY_IMAGE="$2"; shift 2 ;;
        -b|--bind)  HOST_BIND="$2"; shift 2 ;;
        -h|--help)  usage; exit 0 ;;
        *)          echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

docker run --rm --user "$(id -u):0" --name template_registry_container \
    -p $HOST_BIND:8000 $TEMPLATE_REGISTRY_IMAGE
