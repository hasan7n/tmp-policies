set -e

USER_KEYS_FOLDER=""
IMAGE="mlcommons/pdo_base_client:latest"
# list of user names to generate keys for
USER_NAMES="user1 user2 user3 user4 user5 data_owner data_user vc_issuer"

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Generate PDO user keys.

Options:
  -k, --keys-folder DIR    Folder to write user keys into (required)
  -i, --image IMAGE        PDO client image to run (default: $IMAGE)
  -u, --users "U1 U2 ..."  Space-separated user names (default: $USER_NAMES)
  -h, --help               Show this help and exit
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        -k|--keys-folder) USER_KEYS_FOLDER="$2"; shift 2 ;;
        -i|--image)       IMAGE="$2"; shift 2 ;;
        -u|--users)       USER_NAMES="$2"; shift 2 ;;
        -h|--help)        usage; exit 0 ;;
        *)                echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

# Required arguments
[ -n "$USER_KEYS_FOLDER" ] || { echo "Missing required option: -k/--keys-folder" >&2; usage >&2; exit 1; }

# create user keys
docker run --rm --volume ${USER_KEYS_FOLDER}:/tmp/users_keys \
    $IMAGE \
    /scripts/generate_user_keys.sh \
    --keys-folder /tmp/users_keys \
    --users "${USER_NAMES}"
