set -e
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LOG="$SCRIPT_DIR/runserver.log"
ENV_FILE="$SCRIPT_DIR/env.sh"
source "$ENV_FILE"
python "$SCRIPT_DIR/manage.py" bootstrap
python "$SCRIPT_DIR/manage.py" runserver
