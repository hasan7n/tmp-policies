SCRIPT_DIR=$(dirname $(readlink -f ${BASH_SOURCE[0]}))
source ${SCRIPT_DIR}/../setup/activate_pdo_env.sh

bash ${SCRIPT_DIR}/../copy_ledger_and_services_files.sh
TEST_LIST=^system-download-script make -C ${PDO_CONTRACTS_ROOT} test
