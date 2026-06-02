: "${LEDGER_CERT_PATH?Missing environment variable LEDGER_CERT_PATH}"
: "${SITE_TOML_SOURCE?Missing environment variable SITE_TOML_SOURCE}"
: "${F_SERVICE_HOST?Missing environment variable F_SERVICE_HOST}"
: "${PDO_LEDGER_URL?Missing environment variable PDO_LEDGER_URL}"
: "${USER_KEYS_FOLDER?Missing environment variable USER_KEYS_FOLDER}"

docker run --rm --network host --name policies_client_container \
    --volume ${LEDGER_CERT_PATH}:/tmp/networkcert.pem \
    --volume ${SITE_TOML_SOURCE}:/tmp/site.toml \
    --volume ${USER_KEYS_FOLDER}:/tmp/user_keys \
    --env F_SERVICE_HOST=$F_SERVICE_HOST \
    --env LEDGER_CERT_PATH=/tmp/networkcert.pem \
    --env SITE_TOML_SOURCE=/tmp/site.toml \
    --env PDO_LEDGER_URL=$PDO_LEDGER_URL \
    --env USER_KEYS_FOLDER=/tmp/user_keys \
    --entrypoint bash pdo_policies:latest /entrypoint_python.sh