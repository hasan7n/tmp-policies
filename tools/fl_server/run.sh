INTERFACE="0.0.0.0"
PORT="7920"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Run the mock FL server. It has no PDO dependency and needs no container.

Options:
  -n, --interface IFACE    Interface to bind (default: $INTERFACE)
  -p, --port PORT          Port to bind (default: $PORT)
  -h, --help               Show this help and exit
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        -n|--interface) INTERFACE="$2"; shift 2 ;;
        -p|--port)      PORT="$2"; shift 2 ;;
        -h|--help)      usage; exit 0 ;;
        *)              echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

exec python3 -u "${SCRIPT_DIR}/server.py" --interface "$INTERFACE" --port "$PORT"
