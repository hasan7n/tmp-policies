# !/bin/bash
set -e
: "${LEDGER_WS?Missing environment variable LEDGER_WS}"
: "${PDO_LEDGER_IMAGE?Missing environment variable PDO_LEDGER_IMAGE}"
: "${CONTAINER_NETWORK_INTERFACE?Missing environment variable CONTAINER_NETWORK_INTERFACE}"
: "${LEDGER_PORT?Missing environment variable LEDGER_PORT}"

# Cleanup
rm -rf ${LEDGER_WS}
mkdir -p ${LEDGER_WS}/ccf/keys

# Run ledger
docker run --rm --network host --name ccf_container \
    --volume $LEDGER_WS:/project/pdo/xfer/ \
    --entrypoint /project/pdo/tools/start_ccf.sh $PDO_LEDGER_IMAGE -m build -i "$CONTAINER_NETWORK_INTERFACE" --start
