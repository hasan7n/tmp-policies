# !/bin/bash
set -e

SERVICES_WS="/tmp/pdo_services"
LEDGER_CERT_PATH="/tmp/pdo_ledger/ccf/keys/networkcert.pem"
PDO_LEDGER_URL=""
PDO_SERVICES_IMAGE=""
INTERFACE=""

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Run the PDO services container.

Options:
  -w, --workspace DIR      Services workspace dir (default: $SERVICES_WS)
  -c, --cert-path PATH     Ledger cert path to copy in (default: $LEDGER_CERT_PATH)
  -l, --ledger-url URL     Ledger URL (required)
  -i, --image IMAGE        Services image to run (required)
  -n, --interface IFACE    Host network interface (required)
  -h, --help               Show this help and exit
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        -w|--workspace)  SERVICES_WS="$2"; shift 2 ;;
        -c|--cert-path)  LEDGER_CERT_PATH="$2"; shift 2 ;;
        -l|--ledger-url) PDO_LEDGER_URL="$2"; shift 2 ;;
        -i|--image)      PDO_SERVICES_IMAGE="$2"; shift 2 ;;
        -n|--interface)  INTERFACE="$2"; shift 2 ;;
        -h|--help)       usage; exit 0 ;;
        *)               echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

# Required arguments
[ -n "$PDO_LEDGER_URL" ]             || { echo "Missing required option: -l/--ledger-url" >&2; usage >&2; exit 1; }
[ -n "$PDO_SERVICES_IMAGE" ]         || { echo "Missing required option: -i/--image" >&2; usage >&2; exit 1; }
[ -n "$INTERFACE" ] || { echo "Missing required option: -n/--interface" >&2; usage >&2; exit 1; }

# Cleanup
rm -rf ${SERVICES_WS}
mkdir -p ${SERVICES_WS}/services/etc
mkdir -p ${SERVICES_WS}/ccf/keys

# Copy ledger keys
cp -r $LEDGER_CERT_PATH ${SERVICES_WS}/ccf/keys/

# Run services
docker run --rm --network host --name services_container \
    --volume ${SERVICES_WS}:/project/pdo/xfer/ \
    --entrypoint /project/pdo/tools/start_services.sh $PDO_SERVICES_IMAGE -m build -c 5 -i $INTERFACE -l $PDO_LEDGER_URL
