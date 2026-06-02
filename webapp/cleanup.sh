SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
pkill -f "python $SCRIPT_DIR/manage.py runserver"
rm $SCRIPT_DIR/db.sqlite3
rm -rf $SCRIPT_DIR/scratch
python $SCRIPT_DIR/manage.py migrate