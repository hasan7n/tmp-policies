set -e

source ${PDO_SOURCE_ROOT}/build/common-config.sh
source ${PDO_INSTALL_ROOT}/bin/activate
export PDO_JUPYTER_ROOT=${PDO_HOME}/notebooks

mkdir -p $PDO_LEDGER_KEY_ROOT
cp /tmp/ledger_ws/ccf/keys/networkcert.pem $PDO_LEDGER_KEY_ROOT
mkdir -p $PDO_HOME/etc/sites
cp /tmp/ledger_ws/services/etc/site.toml $PDO_HOME/etc/sites/hasan-HP-ZBook-15-G3.toml

TEST_LIST=^system-download make -C ${PDO_CONTRACTS_ROOT} test
# bash $PDO_CONTRACTS_ROOT/download-contract/test/script_test.sh "--loglevel" "warn" "--logfile" "__screen__" "--ledger" "http://127.0.0.1:6600" "--host" "hasan-HP-ZBook-15-G3"