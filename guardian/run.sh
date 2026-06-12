GUARDIAN_IMAGE="mlcommons/toy_guardian:latest"
HOST_BIND="$(hostname -I | awk '{print $1}'):7900"

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Run the guardian container.

Options:
  -i, --image IMAGE        Docker image to run (default: $GUARDIAN_IMAGE)
  -b, --bind IFACE:PORT    Host interface:port to publish (default: $HOST_BIND)
  -h, --help               Show this help and exit
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        -i|--image) GUARDIAN_IMAGE="$2"; shift 2 ;;
        -b|--bind)  HOST_BIND="$2"; shift 2 ;;
        -h|--help)  usage; exit 0 ;;
        *)          echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

# docker run --rm --env F_GUARDIAN_HOST=0.0.0.0 --user "$(id -u):0" \
#     -p $HOST_BIND:7900 --name pdo-guardian $GUARDIAN_IMAGE

docker run --rm --env F_GUARDIAN_HOST=localhost --user "$(id -u):0" \
    --network host --name pdo-guardian $GUARDIAN_IMAGE