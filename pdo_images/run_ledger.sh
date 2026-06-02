# !/bin/bash
set -e
: "${LEDGER_WS?Missing environment variable LEDGER_WS}"

# Cleanup
rm -rf ${LEDGER_WS}
mkdir -p ${LEDGER_WS}/ccf/keys

# Run ledger
docker run --rm --network host --name ccf_container \
    --volume $LEDGER_WS:/project/pdo/xfer/ \
    --entrypoint /project/pdo/tools/start_ccf.sh pdo_ccf:0.4.29 -m build -i localhost --start
