"""PDO environment configuration for the webui.

Mirrors the decentralized test config.py: env vars are set at import time
because ``pdo.*`` modules read ``PDO_HOME`` etc. when they are first
imported. Keep this module's import side-effects intact and import it
*before* any ``pdo.*`` import.
"""

import os

# -----------------------------------------------------------------
# Required environment variables (mirrors decentralized test config.py)
# -----------------------------------------------------------------
required_env_vars = [
    "LEDGER_CERT_PATH",
    "SITE_TOML_SOURCE",
    "PDO_LEDGER_URL",
    "F_SERVICE_HOST",
    "USER_KEYS_FOLDER",
    "PDO_INSTALL_ROOT",
]
for var in required_env_vars:
    if var not in os.environ:
        raise Exception(f"{var} environment variable is required")

##

os.environ.setdefault("PDO_HOME", f"{os.environ['PDO_INSTALL_ROOT']}/opt/pdo")
os.environ.setdefault(
    "PDO_LEDGER_KEY_ROOT", f"{os.environ['PDO_HOME']}/etc/keys/ledger"
)
os.environ.setdefault("PDO_LEDGER_TYPE", "ccf")


# -----------------------------------------------------------------
# Paths and runtime config
# -----------------------------------------------------------------
PDO_INSTALL_ROOT = os.environ["PDO_INSTALL_ROOT"]
PDO_HOME = os.environ["PDO_HOME"]
PDO_LEDGER_KEY_ROOT = os.environ["PDO_LEDGER_KEY_ROOT"]
PDO_LEDGER_URL = os.environ["PDO_LEDGER_URL"]
F_SERVICE_HOST = os.environ["F_SERVICE_HOST"]
LEDGER_CERT_PATH = os.environ["LEDGER_CERT_PATH"]
SITE_TOML_SOURCE = os.environ["SITE_TOML_SOURCE"]
USER_KEYS_FOLDER = os.environ["USER_KEYS_FOLDER"]

WEBUI_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRATCH_DIR = os.path.join(WEBUI_ROOT, "scratch")
DOWNLOAD_OUTPUT_DIR = os.path.join(SCRATCH_DIR, "downloads")

F_SERVICE_SITE_FILE = f"{PDO_HOME}/etc/sites/{F_SERVICE_HOST}.toml"
F_SERVICE_GROUPS_DB_FILE = f"{SCRATCH_DIR}/groups_db"
F_SERVICE_DB_FILE = f"{SCRATCH_DIR}/service_db"
F_LOGFILE = os.environ.get("PDO_LOG_FILE", "__screen__")
F_LOGLEVEL = os.environ.get("PDO_LOG_LEVEL", "warn")

PREFERRED_ESERVICE_URL = os.environ.get("PREFERRED_ESERVICE_URL", "random")
