SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
pkill -f "python $SCRIPT_DIR/manage.py runserver 8002"
rm $SCRIPT_DIR/db.sqlite3
python $SCRIPT_DIR/manage.py migrate