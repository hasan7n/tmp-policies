SCRIPT_DIR=$(dirname $(readlink -f ${BASH_SOURCE[0]}))
source ${SCRIPT_DIR}/env.sh
export PDO_SOURCE_ROOT=${PDO_CONTRACTS_ROOT}/private-data-objects
source ${PDO_SOURCE_ROOT}/build/common-config.sh
source ${PDO_INSTALL_ROOT}/bin/activate
export PDO_JUPYTER_ROOT=${PDO_HOME}/notebooks
