# !/bin/bash
set -e
: "${SERVICES_WS?Missing environment variable SERVICES_WS}"
: "${LEDGER_CERT_PATH?Missing environment variable LEDGER_CERT_PATH}"
: "${PDO_LEDGER_URL?Missing environment variable PDO_LEDGER_URL}"

# Cleanup
rm -rf ${SERVICES_WS}
mkdir -p ${SERVICES_WS}/services/etc
mkdir -p ${SERVICES_WS}/ccf/keys

# Copy ledger keys
cp -r $LEDGER_CERT_PATH ${SERVICES_WS}/ccf/keys

# Run services
docker run --rm --network host --name services_container \
    --volume ${SERVICES_WS}:/project/pdo/xfer/ \
    --entrypoint /project/pdo/tools/start_services.sh pdo_services:0.4.29 -m build -c 5 -i localhost -l $PDO_LEDGER_URL