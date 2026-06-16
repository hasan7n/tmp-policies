WEBAPP_IMAGE=""
INTERFACE=""
PORT=""
LEDGER_CERT_PATH=""
SITE_TOML_SOURCE=""
USER_KEYS_FOLDER=""
SCRATCH_DIR=""
LEDGER_URL=""
SERVICE_HOST=""
ASSET_REGISTRY_URL=""
TEMPLATE_REGISTRY_URL=""

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Run the webapp from the merged PDO client image. Host files and the scratch dir
are bind-mounted onto fixed in-container paths, and configuration is forwarded
to /webapp/run.sh as args (no .env file involved).

Options:
  -i, --image IMAGE              Docker image to run (required)
  -n, --interface IFACE          Host interface to publish (required)
  -p, --port PORT                Host port to publish (required)
  -c, --cert-path PATH           Ledger network cert on the host (required)
  -s, --site-toml PATH           Site toml source on the host (required)
  -k, --keys-folder DIR          User keys folder on the host (required)
  -S, --scratch DIR              Host scratch dir for generated PDO state (required)
  -l, --ledger-url URL           PDO ledger URL (required)
  -H, --service-host HOST        Service site host (required)
  -a, --asset-registry-url URL   Asset registry URL (required)
  -t, --template-registry-url URL Template registry URL (required)
  -h, --help                     Show this help and exit
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        -i|--image)                WEBAPP_IMAGE="$2"; shift 2 ;;
        -n|--interface)            INTERFACE="$2"; shift 2 ;;
        -p|--port)                 PORT="$2"; shift 2 ;;
        -c|--cert-path)            LEDGER_CERT_PATH="$2"; shift 2 ;;
        -s|--site-toml)            SITE_TOML_SOURCE="$2"; shift 2 ;;
        -k|--keys-folder)          USER_KEYS_FOLDER="$2"; shift 2 ;;
        -S|--scratch)              SCRATCH_DIR="$2"; shift 2 ;;
        -l|--ledger-url)           LEDGER_URL="$2"; shift 2 ;;
        -H|--service-host)         SERVICE_HOST="$2"; shift 2 ;;
        -a|--asset-registry-url)   ASSET_REGISTRY_URL="$2"; shift 2 ;;
        -t|--template-registry-url) TEMPLATE_REGISTRY_URL="$2"; shift 2 ;;
        -h|--help)                 usage; exit 0 ;;
        *)                         echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

# Required arguments
[ -n "$WEBAPP_IMAGE" ]          || { echo "Missing required option: -i/--image" >&2; usage >&2; exit 1; }
[ -n "$INTERFACE" ]             || { echo "Missing required option: -n/--interface" >&2; usage >&2; exit 1; }
[ -n "$PORT" ]                  || { echo "Missing required option: -p/--port" >&2; usage >&2; exit 1; }
[ -n "$LEDGER_CERT_PATH" ]      || { echo "Missing required option: -c/--cert-path" >&2; usage >&2; exit 1; }
[ -n "$SITE_TOML_SOURCE" ]      || { echo "Missing required option: -s/--site-toml" >&2; usage >&2; exit 1; }
[ -n "$USER_KEYS_FOLDER" ]      || { echo "Missing required option: -k/--keys-folder" >&2; usage >&2; exit 1; }
[ -n "$SCRATCH_DIR" ]           || { echo "Missing required option: -S/--scratch" >&2; usage >&2; exit 1; }
[ -n "$LEDGER_URL" ]            || { echo "Missing required option: -l/--ledger-url" >&2; usage >&2; exit 1; }
[ -n "$SERVICE_HOST" ]          || { echo "Missing required option: -H/--service-host" >&2; usage >&2; exit 1; }
[ -n "$ASSET_REGISTRY_URL" ]    || { echo "Missing required option: -a/--asset-registry-url" >&2; usage >&2; exit 1; }
[ -n "$TEMPLATE_REGISTRY_URL" ] || { echo "Missing required option: -t/--template-registry-url" >&2; usage >&2; exit 1; }

# Ensure the host scratch dir exists so the bind mount has a source.
mkdir -p "$SCRATCH_DIR"

# Bind-mount host files onto fixed container paths, then forward those paths
# (and the rest of the config) to /webapp/run.sh as args. PDO_INSTALL_ROOT and
# PDO_CONTRACTS_ROOT come from the image, so run.sh needs no --install-root.
docker run --rm --user "$(id -u):0" --name policies_web_client \
    -p $INTERFACE:$PORT:8000 \
    --volume ${LEDGER_CERT_PATH}:/tmp/networkcert.pem \
    --volume ${SITE_TOML_SOURCE}:/tmp/site.toml \
    --volume ${USER_KEYS_FOLDER}:/tmp/user_keys \
    --volume ${SCRATCH_DIR}:/tmp/scratch \
    $WEBAPP_IMAGE /webapp/run.sh \
        --interface 0.0.0.0 --port 8000 \
        --ledger-url "$LEDGER_URL" \
        --service-host "$SERVICE_HOST" \
        --cert-path /tmp/networkcert.pem \
        --site-toml /tmp/site.toml \
        --keys-folder /tmp/user_keys \
        --scratch /tmp/scratch \
        --asset-registry-url "$ASSET_REGISTRY_URL" \
        --template-registry-url "$TEMPLATE_REGISTRY_URL"
