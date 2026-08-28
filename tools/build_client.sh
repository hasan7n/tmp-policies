export PDO_INSTALL_ROOT=/home/hasan/work/pdos/pdo_install
export PDO_CONTRACTS_ROOT=/home/hasan/work/pdos/pdo-contracts
# bash pdo_client/scripts/cleanup.sh
bash pdo_client/setup/setup.sh \
    --families "exchange-contract identity-contract authority-contract rego-contract"

# build bare metal guardians (guardians/public and fl_server need no install)
bash guardians/download/setup.sh
bash guardians/inference/setup.sh

# build  webui
bash pdo_client/webapp/setup.sh