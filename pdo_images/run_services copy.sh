# !/bin/bash

# Workspace folders
SERVICES_WS=/tmp/services_ws
LEDGER_CERT=/tmp/ledger_ws/ccf/keys/networkcert.pem

# Ledger URL
LEDGER_URL="http://127.0.0.1:6600"

# Cleanup
rm -rf ${SERVICES_WS}
mkdir -p ${SERVICES_WS}/services/etc
mkdir -p ${SERVICES_WS}/ccf/keys

# Copy ledger keys
cp -r $LEDGER_CERT ${SERVICES_WS}/ccf/keys

# Run services
docker run --rm --network host --name services_container \
    --volume ${SERVICES_WS}:/project/pdo/xfer/ \
    --entrypoint /project/pdo/tools/start_services.sh pdo_services:0.4.29 -m build -c 5 -i localhost -l $LEDGER_URL