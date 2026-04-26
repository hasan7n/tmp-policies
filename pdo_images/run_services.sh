# !/bin/bash

# Workspace folders
LEDGER_WS=/tmp/ledger_ws

# Ledger URL
LEDGER_URL="http://127.0.0.1:6600"

# Cleanup
mkdir -p ${LEDGER_WS}/services/etc

# Run services
docker run --rm --network host --name services_container \
    --volume ${LEDGER_WS}:/project/pdo/xfer/ \
    --entrypoint /project/pdo/tools/start_services.sh pdo_services:0.4.29 -m build -c 5 -i localhost -l $LEDGER_URL