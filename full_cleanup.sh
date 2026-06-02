set -e

: "${LEDGER_WS?Missing environment variable LEDGER_WS}"
: "${SERVICES_WS?Missing environment variable SERVICES_WS}"

docker container stop ccf_container
docker container stop services_container
docker container stop pdo-guardian
rm -rf $LEDGER_WS
rm -rf $SERVICES_WS
bash client_app/cleanup.sh
bash asset_registry/cleanup.sh
bash template_registry/cleanup.sh