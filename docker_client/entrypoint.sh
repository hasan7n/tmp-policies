set -e

: "${LEDGER_CERT_PATH?Missing environment variable LEDGER_CERT_PATH}"
: "${SITE_TOML_SOURCE?Missing environment variable SITE_TOML_SOURCE}"
: "${PDO_INSTALL_ROOT?Missing environment variable PDO_INSTALL_ROOT}"
: "${PDO_SOURCE_ROOT?Missing environment variable PDO_SOURCE_ROOT}"
: "${F_SERVICE_HOST?Missing environment variable F_SERVICE_HOST}"

source ${PDO_SOURCE_ROOT}/build/common-config.sh
source ${PDO_INSTALL_ROOT}/bin/activate
export PDO_JUPYTER_ROOT=${PDO_HOME}/notebooks

mkdir -p $PDO_LEDGER_KEY_ROOT
cp $LEDGER_CERT_PATH $PDO_LEDGER_KEY_ROOT/networkcert.pem
mkdir -p $PDO_HOME/etc/sites
cp $SITE_TOML_SOURCE $PDO_HOME/etc/sites/$F_SERVICE_HOST.toml

TEST_LIST=^system-download make -C ${PDO_CONTRACTS_ROOT} test
