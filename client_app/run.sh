set -e
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LOG="$SCRIPT_DIR/runserver.log"
python "$SCRIPT_DIR/manage.py" bootstrap
python "$SCRIPT_DIR/manage.py" runserver
