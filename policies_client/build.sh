export PDO_CONTRACTS_ROOT=/home/hasan/work/pdos/pdo-contracts
export PDO_INSTALL_ROOT=/home/hasan/work/pdos/pdo_install
export PDO_SOURCE_ROOT=${PDO_CONTRACTS_ROOT}/private-data-objects
source ${PDO_SOURCE_ROOT}/build/common-config.sh
source ${PDO_INSTALL_ROOT}/bin/activate
export PDO_JUPYTER_ROOT=${PDO_HOME}/notebooks


echo "SET(CONTRACT_FAMILIES exchange-contract identity-contract download-contract)" \
    > $PDO_CONTRACTS_ROOT/Local.cmake


make -C ${PDO_CONTRACTS_ROOT}
make -C ${PDO_CONTRACTS_ROOT} install