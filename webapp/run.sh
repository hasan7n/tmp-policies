SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
INTERFACE=""
PORT=""

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Run migrations, bootstrap the local PDO state, then start the dev server.
Configuration is read from $SCRIPT_DIR/.env (see .env.example).

Options:
  -n, --interface IFACE    Interface for the dev server (required)
  -p, --port PORT          Port for the dev server (required)
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

# Required arguments
[ -n "$INTERFACE" ] || { echo "Missing required option: -n/--interface" >&2; usage >&2; exit 1; }
[ -n "$PORT" ]      || { echo "Missing required option: -p/--port" >&2; usage >&2; exit 1; }

python $SCRIPT_DIR/manage.py migrate
python $SCRIPT_DIR/manage.py bootstrap
exec python -u "$SCRIPT_DIR/manage.py" runserver "$INTERFACE:$PORT"
