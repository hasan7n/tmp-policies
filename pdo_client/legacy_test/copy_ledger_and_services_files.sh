set -e

: "${LEDGER_CERT_PATH?Missing environment variable LEDGER_CERT_PATH}"
: "${SITE_TOML_SOURCE?Missing environment variable SITE_TOML_SOURCE}"
: "${F_SERVICE_HOST?Missing environment variable F_SERVICE_HOST}"

SCRIPT_DIR=$(dirname $(readlink -f ${BASH_SOURCE[0]}))
source ${SCRIPT_DIR}/../setup/env.sh

mkdir -p $PDO_LEDGER_KEY_ROOT
cp $LEDGER_CERT_PATH $PDO_LEDGER_KEY_ROOT
mkdir -p $PDO_HOME/etc/sites
cp $SITE_TOML_SOURCE $PDO_HOME/etc/sites/${F_SERVICE_HOST}.toml

