SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BIND="127.0.0.1:8001"

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Run migrations, seed the dev admin user, then start the dev server.

Options:
  -b, --bind IFACE:PORT    Interface:port for the dev server (default: $BIND)
  -h, --help               Show this help and exit
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        -b|--bind) BIND="$2"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *)         echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

python $SCRIPT_DIR/manage.py migrate
# Dev-only admin user for the Django admin dashboard at /admin/.
DJANGO_SUPERUSER_USERNAME=admin DJANGO_SUPERUSER_PASSWORD=admin \
DJANGO_SUPERUSER_EMAIL=admin@example.com \
python $SCRIPT_DIR/manage.py createsuperuser --noinput
exec python -u "$SCRIPT_DIR/manage.py" runserver "$BIND"
