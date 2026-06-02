export LEDGER_WS=${LEDGER_WS:-/tmp/ledger_ws}
export SERVICES_WS=${SERVICES_WS:-/tmp/services_ws}
export LEDGER_CERT_PATH=${LEDGER_CERT_PATH:-/tmp/ledger_ws/ccf/keys/networkcert.pem}
export SITE_TOML_SOURCE=${SITE_TOML_SOURCE:-/tmp/services_ws/services/etc/site.toml}
export USER_KEYS_FOLDER=${USER_KEYS_FOLDER:-/home/hasan/work/pdos/user_keys}
export PREFERRED_ESERVICE_URL=${PREFERRED_ESERVICE_URL:-random}
export CONTAINER_NETWORK_INTERFACE=${CONTAINER_NETWORK_INTERFACE:-192.168.1.223}
export F_SERVICE_HOST=${F_SERVICE_HOST:-$CONTAINER_NETWORK_INTERFACE}
export F_GUARDIAN_HOST=${F_GUARDIAN_HOST:-$CONTAINER_NETWORK_INTERFACE}

export LEDGER_PORT=${LEDGER_PORT:-6600}  # KEEP IT 6600
export GUARDIAN_PORT=${GUARDIAN_PORT:-7900}
export ASSET_REGISTRY_PORT=${ASSET_REGISTRY_PORT:-8001}
export TEMPLATE_REGISTRY_PORT=${TEMPLATE_REGISTRY_PORT:-8002}
export WEBAPP_PORT=${WEBAPP_PORT:-8000}

export PDO_LEDGER_URL=${PDO_LEDGER_URL:-http://$CONTAINER_NETWORK_INTERFACE:$LEDGER_PORT}

export ASSET_REGISTRY_IMAGE=${ASSET_REGISTRY_IMAGE:-"mlcommons/pdo_toy_asset_registry:latest"}
export TEMPLATE_REGISTRY_IMAGE=${TEMPLATE_REGISTRY_IMAGE:-"mlcommons/pdo_toy_template_registry:latest"}
export WEBAPP_IMAGE=${WEBAPP_IMAGE:-"mlcommons/pdo_webapp:latest"}
export PDO_LEDGER_IMAGE=${PDO_LEDGER_IMAGE:-"mlcommons/pdo_ledger:latest"}
export PDO_SERVICES_IMAGE=${PDO_SERVICES_IMAGE:-"mlcommons/pdo_services:latest"}
export GUARDIAN_IMAGE=${GUARDIAN_IMAGE:-"mlcommons/toy_guardian:latest"}
export PDO_CLIENT_IMAGE=${PDO_CLIENT_IMAGE:-"mlcommons/pdo_base_client:latest"}