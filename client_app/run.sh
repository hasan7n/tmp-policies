SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
python -u "$SCRIPT_DIR/manage.py" runserver > "$SCRIPT_DIR/runserver.log" 2>&1