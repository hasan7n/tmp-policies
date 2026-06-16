set -e
INTERFACE="$(hostname -I | awk '{print $1}')"

rm -rf /tmp/pdo_ledger
rm -rf /tmp/pdo_services

mkdir -p /tmp/pdo_ledger
mkdir -p /tmp/pdo_services

bash policy_engine/run_ledger.sh \
    --image "mlcommons/pdo_ledger:latest" \
    --interface $INTERFACE \
    --port "6600" \
    --workspace /tmp/pdo_ledger &
sleep 10
# ports are always 7001 -> 7005, 7101 -> 7105, 7201 -> 7205
bash policy_engine/run_services.sh \
    --image "mlcommons/pdo_services:latest" \
    --interface $INTERFACE \
    --ledger-url http://$INTERFACE:6600 \
    --workspace /tmp/pdo_services &
sleep 15
