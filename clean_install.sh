SCRIPTDIR=$(dirname $(readlink -f $0))
source ${SCRIPTDIR}/env.sh
rm -rf ${PDO_INSTALL_ROOT}
rm -rf ${PDO_CONTRACTS_ROOT}/build