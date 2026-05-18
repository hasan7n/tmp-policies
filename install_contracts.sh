SCRIPT_DIR=$(dirname $(readlink -f $0))
source ${SCRIPT_DIR}/activate_pdo_env.sh
make -C ${PDO_CONTRACTS_ROOT}
make -C ${PDO_CONTRACTS_ROOT} install
${PDO_INSTALL_ROOT}/bin/pip install lmdb==1.7.5
${PDO_INSTALL_ROOT}/bin/pip install -r ${SCRIPT_DIR}/client_app/requirements.txt