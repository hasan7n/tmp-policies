ASSET_REGISTRY_IMAGE="mlcommons/pdo_toy_asset_registry:latest"

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Build the asset_registry Docker image.

Options:
  -i, --image IMAGE        Image tag to build (default: $ASSET_REGISTRY_IMAGE)
  -h, --help               Show this help and exit
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        -i|--image) ASSET_REGISTRY_IMAGE="$2"; shift 2 ;;
        -h|--help)  usage; exit 0 ;;
        *)          echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

docker build -t $ASSET_REGISTRY_IMAGE -f ./Dockerfile .
