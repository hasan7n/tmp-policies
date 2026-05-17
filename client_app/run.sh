SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LOG="$SCRIPT_DIR/runserver.log"
python -u "$SCRIPT_DIR/manage.py" bootstrap > "$LOG" 2>&1 || exit 1
python -u "$SCRIPT_DIR/manage.py" runserver >> "$LOG" 2>&1
