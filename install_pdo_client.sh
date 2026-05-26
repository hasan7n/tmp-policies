set -e
# some env vars
SCRIPT_DIR=$(dirname $(readlink -f $0))
source ${SCRIPT_DIR}/env.sh

export PDO_SOURCE_ROOT=${PDO_CONTRACTS_ROOT}/private-data-objects
source ${PDO_SOURCE_ROOT}/build/common-config.sh

# build and install the PDO client
make -C ${PDO_SOURCE_ROOT}/build client

# install pckages to use jupyter?
${PDO_INSTALL_ROOT}/bin/pip install jupyterlab papermill ipywidgets jupytext
