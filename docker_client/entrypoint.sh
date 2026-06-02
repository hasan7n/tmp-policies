set -e

: "${LEDGER_CERT_PATH?Missing environment variable LEDGER_CERT_PATH}"
: "${SITE_TOML_SOURCE?Missing environment variable SITE_TOML_SOURCE}"
: "${PDO_INSTALL_ROOT?Missing environment variable PDO_INSTALL_ROOT}"
: "${PDO_SOURCE_ROOT?Missing environment variable PDO_SOURCE_ROOT}"
: "${F_SERVICE_HOST?Missing environment variable F_SERVICE_HOST}"
: "${PDO_LEDGER_URL?Missing environment variable PDO_LEDGER_URL}"
: "${PREFERRED_ESERVICE_URL?Missing environment variable PREFERRED_ESERVICE_URL}"

source ${PDO_SOURCE_ROOT}/build/common-config.sh
source ${PDO_INSTALL_ROOT}/bin/activate
export PDO_JUPYTER_ROOT=${PDO_HOME}/notebooks

mkdir -p $PDO_LEDGER_KEY_ROOT
cp $LEDGER_CERT_PATH $PDO_LEDGER_KEY_ROOT/networkcert.pem
mkdir -p $PDO_HOME/etc/sites
cp $SITE_TOML_SOURCE $PDO_HOME/etc/sites/$F_SERVICE_HOST.toml

bash $PDO_CONTRACTS_ROOT/download-contract/test/script_test.sh \
    "--loglevel" "warn" \
    "--logfile" "__screen__" \
    "--ledger" "$PDO_LEDGER_URL" \
    "--host" "$F_SERVICE_HOST" \
    "-p" "$PREFERRED_ESERVICE_URL"
