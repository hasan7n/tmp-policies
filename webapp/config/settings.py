import os
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

# Load configuration from a .env file. read_env() populates os.environ so the
# pdo.* layer (which reads PDO_* env vars at import time) sees the same values.
# Settings are loaded during django.setup(), before any pdo.* import, so the
# environment is fully prepared by the time those modules load.
env = environ.Env()
env_file = os.path.join(BASE_DIR, ".env")
if os.path.isfile(env_file):
    env.read_env(env_file)

SECRET_KEY = "django-insecure-client-app-key-change-in-production"
DEBUG = True
ALLOWED_HOSTS = ["*"]

# -----------------------------------------------------------------
# PDO + service configuration (formerly app/pdo_config.py).
# Every value is required and read from the environment (.env); there are no
# defaults. See .env.example (docker) and .env.local.example (bare metal).
# -----------------------------------------------------------------
PDO_INSTALL_ROOT = env("PDO_INSTALL_ROOT")
PDO_LEDGER_URL = env("PDO_LEDGER_URL")
PDO_LEDGER_TYPE = env("PDO_LEDGER_TYPE")
F_SERVICE_HOST = env("F_SERVICE_HOST")
LEDGER_CERT_PATH = env("LEDGER_CERT_PATH")
SITE_TOML_SOURCE = env("SITE_TOML_SOURCE")
USER_KEYS_FOLDER = env("USER_KEYS_FOLDER")
PREFERRED_ESERVICE_URL = env("PREFERRED_ESERVICE_URL")
ASSET_REGISTRY_URL = env("ASSET_REGISTRY_URL")
TEMPLATE_REGISTRY_URL = env("TEMPLATE_REGISTRY_URL")
F_LOGFILE = env("PDO_LOG_FILE")
F_LOGLEVEL = env("PDO_LOG_LEVEL")

# The ledger URL is a single value; LEDGER_URL is an alias for display use.
LEDGER_URL = PDO_LEDGER_URL

# Derived PDO paths.
PDO_HOME = f"{PDO_INSTALL_ROOT}/opt/pdo"
PDO_LEDGER_KEY_ROOT = f"{PDO_HOME}/etc/keys/ledger"

# pdo.* libraries read these from the process environment at import time, so
# mirror the resolved values into os.environ before any pdo.* import.
os.environ["PDO_INSTALL_ROOT"] = PDO_INSTALL_ROOT
os.environ["PDO_HOME"] = PDO_HOME
os.environ["PDO_LEDGER_KEY_ROOT"] = PDO_LEDGER_KEY_ROOT
os.environ["PDO_LEDGER_TYPE"] = PDO_LEDGER_TYPE
os.environ["PDO_LEDGER_URL"] = PDO_LEDGER_URL

# Scratch + derived file locations used by the PDO helpers.
SCRATCH_DIR = str(BASE_DIR / "scratch")
DOWNLOAD_OUTPUT_DIR = os.path.join(SCRATCH_DIR, "downloads")
F_SERVICE_SITE_FILE = f"{PDO_HOME}/etc/sites/{F_SERVICE_HOST}.toml"
F_SERVICE_GROUPS_DB_FILE = f"{SCRATCH_DIR}/groups_db"
F_SERVICE_DB_FILE = f"{SCRATCH_DIR}/service_db"

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.staticfiles",
    "app.apps.ClientAppConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.template.context_processors.csrf",
                "app.context_processors.app_context",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SESSION_ENGINE = "django.contrib.sessions.backends.db"
