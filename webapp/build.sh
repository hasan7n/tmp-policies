WEBAPP_IMAGE=""
PDO_CLIENT_IMAGE=""

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Build the webapp Docker image (FROM the PDO client image).

Options:
  -i, --image IMAGE          Image tag to build (required)
  -c, --client-image IMAGE   PDO client base image (required)
  -h, --help                 Show this help and exit
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        -i|--image)        WEBAPP_IMAGE="$2"; shift 2 ;;
        -c|--client-image) PDO_CLIENT_IMAGE="$2"; shift 2 ;;
        -h|--help)         usage; exit 0 ;;
        *)                 echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

# Required arguments
[ -n "$WEBAPP_IMAGE" ] || { echo "Missing required option: -i/--image" >&2; usage >&2; exit 1; }
[ -n "$PDO_CLIENT_IMAGE" ] || { echo "Missing required option: -c/--client-image" >&2; usage >&2; exit 1; }

docker build --build-arg PDO_CLIENT_IMAGE=$PDO_CLIENT_IMAGE -t $WEBAPP_IMAGE -f ./Dockerfile .
