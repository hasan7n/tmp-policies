set -e
SCRIPT_DIR=$(dirname $(readlink -f ${BASH_SOURCE[0]}))
source ${SCRIPT_DIR}/setup/activate_pdo_env.sh

: "${USER_KEYS_FOLDER?Missing environment variable USER_KEYS_FOLDER}"
: "${PDO_CONTRACTS_ROOT?Missing environment variable PDO_CONTRACTS_ROOT}"

# NOTE: first should Run ledger and services and guardian


bash $SCRIPT_DIR/../generate_user_keys.sh
python ${PDO_CONTRACTS_ROOT}/download-contract/test/python_test/startup.py
python ${PDO_CONTRACTS_ROOT}/download-contract/test/python_test/stateless_test.py
python ${PDO_CONTRACTS_ROOT}/download-contract/test/python_test/cleanup.py
