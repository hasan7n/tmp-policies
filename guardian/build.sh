PDO_CLIENT_IMAGE="mlcommons/pdo_base_client:latest"
GUARDIAN_IMAGE="mlcommons/toy_guardian:latest"

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Build the guardian Docker image.

Options:
  -c, --client-image IMAGE   Base PDO client image (default: $PDO_CLIENT_IMAGE)
  -i, --image IMAGE          Image tag to build (default: $GUARDIAN_IMAGE)
  -h, --help                 Show this help and exit
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        -c|--client-image) PDO_CLIENT_IMAGE="$2"; shift 2 ;;
        -i|--image)        GUARDIAN_IMAGE="$2"; shift 2 ;;
        -h|--help)         usage; exit 0 ;;
        *)                 echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

docker build --build-arg PDO_CLIENT_IMAGE=$PDO_CLIENT_IMAGE -f Dockerfile -t $GUARDIAN_IMAGE .