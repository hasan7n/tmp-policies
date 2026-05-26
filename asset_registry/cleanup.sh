SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
pkill -f "python $SCRIPT_DIR/manage.py runserver 8001"
rm $SCRIPT_DIR/db.sqlite3
python $SCRIPT_DIR/manage.py migrate
# Dev-only admin user for the Django admin dashboard at /admin/.
DJANGO_SUPERUSER_USERNAME=admin DJANGO_SUPERUSER_PASSWORD=admin \
DJANGO_SUPERUSER_EMAIL=admin@example.com \
python $SCRIPT_DIR/manage.py createsuperuser --noinput