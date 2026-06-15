SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
WEBAPP_IMAGE=""
INTERFACE=""
PORT=""
LEDGER_CERT_PATH=""
SITE_TOML_SOURCE=""
USER_KEYS_FOLDER=""

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Run the webapp container. Service configuration is read from
$SCRIPT_DIR/.env (mounted into the container; see .env.example). Host PDO
input files are bind-mounted onto the fixed in-container paths.

Options:
  -i, --image IMAGE        Docker image to run (required)
  -n, --interface IFACE    Host interface to publish (required)
  -p, --port PORT          Host port to publish (required)
  -c, --cert-path PATH     Ledger network cert (required)
  -s, --site-toml PATH     Site toml source (required)
  -k, --keys-folder DIR    Existing user keys folder to mount (required)
  -h, --help               Show this help and exit
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        -i|--image)       WEBAPP_IMAGE="$2"; shift 2 ;;
        -n|--interface)   INTERFACE="$2"; shift 2 ;;
        -p|--port)        PORT="$2"; shift 2 ;;
        -c|--cert-path)   LEDGER_CERT_PATH="$2"; shift 2 ;;
        -s|--site-toml)   SITE_TOML_SOURCE="$2"; shift 2 ;;
        -k|--keys-folder) USER_KEYS_FOLDER="$2"; shift 2 ;;
        -h|--help)        usage; exit 0 ;;
        *)                echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

# Required arguments
[ -n "$WEBAPP_IMAGE" ]     || { echo "Missing required option: -i/--image" >&2; usage >&2; exit 1; }
[ -n "$INTERFACE" ]        || { echo "Missing required option: -n/--interface" >&2; usage >&2; exit 1; }
[ -n "$PORT" ]             || { echo "Missing required option: -p/--port" >&2; usage >&2; exit 1; }
[ -n "$LEDGER_CERT_PATH" ] || { echo "Missing required option: -c/--cert-path" >&2; usage >&2; exit 1; }
[ -n "$SITE_TOML_SOURCE" ] || { echo "Missing required option: -s/--site-toml" >&2; usage >&2; exit 1; }
[ -n "$USER_KEYS_FOLDER" ] || { echo "Missing required option: -k/--keys-folder" >&2; usage >&2; exit 1; }

docker run --rm --user "$(id -u):0" --name policies_web_client \
    -p $INTERFACE:$PORT:8000 \
    --volume ${LEDGER_CERT_PATH}:/tmp/networkcert.pem \
    --volume ${SITE_TOML_SOURCE}:/tmp/site.toml \
    --volume ${USER_KEYS_FOLDER}:/tmp/user_keys \
    --volume ${SCRIPT_DIR}/.env:/webapp/.env:ro \
    $WEBAPP_IMAGE
