: "${LEDGER_CERT_PATH?Missing environment variable LEDGER_CERT_PATH}"
: "${SITE_TOML_SOURCE?Missing environment variable SITE_TOML_SOURCE}"
: "${F_SERVICE_HOST?Missing environment variable F_SERVICE_HOST}"

docker run --rm --network host --name policies_client_container \
    --volume ${LEDGER_CERT_PATH}:/tmp/cert.pem \
    --volume ${SITE_TOML_SOURCE}:/tmp/site.toml \
    --env F_SERVICE_HOST=$F_SERVICE_HOST \
    --env LEDGER_CERT_PATH=/tmp/cert.pem \
    --env SITE_TOML_SOURCE=/tmp/site.toml \
    pdo_policies:latest