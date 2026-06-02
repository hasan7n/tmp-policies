# Minimal image for the template_registry Django toy server.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings

WORKDIR /app

# Install deps first so code changes don't bust the pip layer.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the app (includes config/seed_data.json that migration 0002 reads).
COPY . .

# Non-root user + group 0 access so any host uid can read/write mounted
# volumes when launched with `--user $(id -u):0`. New files written at
# runtime inherit gid 0 from the process's egid.
RUN useradd -m -u 1000 app && \
    chgrp -R 0 /app && chmod -R g=u /app
USER 1000:0

# Migrate (creates SQLite + runs the seed migration) then start the dev server.
# exec ensures SIGTERM reaches Django, not the shell.
CMD ["bash", "-c", "python manage.py migrate --noinput && DJANGO_SUPERUSER_USERNAME=admin DJANGO_SUPERUSER_PASSWORD=admin DJANGO_SUPERUSER_EMAIL=admin@example.com python manage.py createsuperuser --noinput && exec python -u manage.py runserver 0.0.0.0:8000"]
