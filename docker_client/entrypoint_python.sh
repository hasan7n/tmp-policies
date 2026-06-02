set -e

: "${LEDGER_CERT_PATH?Missing environment variable LEDGER_CERT_PATH}"
: "${SITE_TOML_SOURCE?Missing environment variable SITE_TOML_SOURCE}"
: "${PDO_INSTALL_ROOT?Missing environment variable PDO_INSTALL_ROOT}"
: "${PDO_SOURCE_ROOT?Missing environment variable PDO_SOURCE_ROOT}"
: "${F_SERVICE_HOST?Missing environment variable F_SERVICE_HOST}"
: "${PDO_LEDGER_URL?Missing environment variable PDO_LEDGER_URL}"
: "${USER_KEYS_FOLDER?Missing environment variable USER_KEYS_FOLDER}"

source ${PDO_SOURCE_ROOT}/build/common-config.sh
source ${PDO_INSTALL_ROOT}/bin/activate
export PDO_JUPYTER_ROOT=${PDO_HOME}/notebooks

python ${PDO_CONTRACTS_ROOT}/download-contract/test/python/startup.py
python ${PDO_CONTRACTS_ROOT}/download-contract/test/python/stateless_test.py