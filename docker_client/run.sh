: "${LEDGER_CERT_PATH?Missing environment variable LEDGER_CERT_PATH}"
: "${SITE_TOML_SOURCE?Missing environment variable SITE_TOML_SOURCE}"
: "${F_SERVICE_HOST?Missing environment variable F_SERVICE_HOST}"
: "${PDO_LEDGER_URL?Missing environment variable PDO_LEDGER_URL}"

docker run --rm --network host --name policies_client_container \
    --user "$(id -u):0" \
    --volume ${LEDGER_CERT_PATH}:/tmp/cert.pem \
    --volume ${SITE_TOML_SOURCE}:/tmp/site.toml \
    --env F_SERVICE_HOST=$F_SERVICE_HOST \
    --env LEDGER_CERT_PATH=/tmp/cert.pem \
    --env SITE_TOML_SOURCE=/tmp/site.toml \
    --env PDO_LEDGER_URL=$PDO_LEDGER_URL \
    pdo_policies:latest