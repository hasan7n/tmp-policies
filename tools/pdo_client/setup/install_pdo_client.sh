set -e
# Build and install the PDO client, plus the jupyter tooling.
: "${PDO_INSTALL_ROOT:?Missing environment variable PDO_INSTALL_ROOT}"
: "${PDO_CONTRACTS_ROOT:?Missing environment variable PDO_CONTRACTS_ROOT}"
export PDO_SOURCE_ROOT=${PDO_CONTRACTS_ROOT}/private-data-objects

source ${PDO_SOURCE_ROOT}/build/common-config.sh
make -C ${PDO_SOURCE_ROOT}/build client
${PDO_INSTALL_ROOT}/bin/pip install jupyterlab papermill ipywidgets jupytext
# Fix lmdb issue
${PDO_INSTALL_ROOT}/bin/pip install lmdb==1.7.5
