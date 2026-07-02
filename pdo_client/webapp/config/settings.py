import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def _require_env(name):
    """Return the named environment variable or raise.

    All configuration is passed via the environment; run.sh / run_docker.sh
    take it as args and export it before launch (there is no .env file).
    Settings load during django.setup(), before any pdo.* import, so the
    environment is fully prepared by the time those modules load.
    """
    try:
        return os.environ[name]
    except KeyError:
        raise ImproperlyConfigured(f"Required environment variable {name} is not set")

SECRET_KEY = "django-insecure-client-app-key-change-in-production"
DEBUG = True
ALLOWED_HOSTS = ["*"]

# -----------------------------------------------------------------
# PDO + service configuration (formerly app/pdo_config.py).
# Every value is required and read from the environment; there are no defaults.
# -----------------------------------------------------------------
PDO_LEDGER_URL = _require_env("PDO_LEDGER_URL")
PDO_LEDGER_TYPE = _require_env("PDO_LEDGER_TYPE")
F_SERVICE_HOST = _require_env("F_SERVICE_HOST")
LEDGER_CERT_PATH = _require_env("LEDGER_CERT_PATH")
SITE_TOML_SOURCE = _require_env("SITE_TOML_SOURCE")
USER_KEYS_FOLDER = _require_env("USER_KEYS_FOLDER")
PREFERRED_ESERVICE_URL = _require_env("PREFERRED_ESERVICE_URL")
ASSET_REGISTRY_URL = _require_env("ASSET_REGISTRY_URL")
TEMPLATE_REGISTRY_URL = _require_env("TEMPLATE_REGISTRY_URL")
SCRATCH_DIR = _require_env("SCRATCH_DIR")
F_LOGFILE = _require_env("PDO_LOG_FILE")
F_LOGLEVEL = _require_env("PDO_LOG_LEVEL")

# PDO install roots are expected in the environment (set in the image; exported
# by the caller for a bare-metal run). PDO_CONTRACTS_ROOT is consumed by the
# pdo.* layer, so validate it here too.
PDO_INSTALL_ROOT = _require_env("PDO_INSTALL_ROOT")
_require_env("PDO_CONTRACTS_ROOT")
PDO_HOME = f"{PDO_INSTALL_ROOT}/opt/pdo"
PDO_LEDGER_KEY_ROOT = f"{PDO_HOME}/etc/keys/ledger"
F_SERVICE_SITE_FILE = f"{PDO_HOME}/etc/sites/{F_SERVICE_HOST}.toml"

# pdo.* libraries read these from the process environment at import time, so
# mirror the resolved values into os.environ before any pdo.* import.
os.environ["PDO_HOME"] = PDO_HOME
os.environ["PDO_LEDGER_KEY_ROOT"] = PDO_LEDGER_KEY_ROOT
os.environ["PDO_LEDGER_TYPE"] = PDO_LEDGER_TYPE
os.environ["PDO_LEDGER_URL"] = PDO_LEDGER_URL

# Derived file locations under the (env-provided) scratch directory.
DOWNLOAD_OUTPUT_DIR = os.path.join(SCRATCH_DIR, "downloads")
F_SERVICE_GROUPS_DB_FILE = f"{SCRATCH_DIR}/groups_db"
F_SERVICE_DB_FILE = f"{SCRATCH_DIR}/service_db"

# Per-user channel keys (RSA key pairs used to receive downloaded data). Each
# user's keys live under CHANNEL_KEYS_DIR/<user_name>/.
CHANNEL_KEYS_DIR = os.path.join(SCRATCH_DIR, "channel_keys")

# Guardian deployment: the owner "deploy behind a guardian" action shells out to
# guardian/run.sh. It defaults to the sibling guardian directory in the repo but
# can be overridden via the environment. The guardian is published on
# GUARDIAN_PORT at F_SERVICE_HOST (the service host the webapp is configured with).
GUARDIAN_DIR = os.environ.get("GUARDIAN_DIR", str(BASE_DIR.parent.parent / "guardian"))
GUARDIAN_IMAGE = os.environ.get("GUARDIAN_IMAGE", "mlcommons/toy_guardian:latest")
GUARDIAN_PORT = os.environ.get("GUARDIAN_PORT", "7900")
GUARDIAN_SSERVICE_PORT = os.environ.get("GUARDIAN_SSERVICE_PORT", "7901")

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
