docker container stop ccf_container
docker container stop services_container
docker container stop pdo-guardian
rm -rf /tmp/ledger_ws
bash client_app/cleanup.sh
bash asset_registry/cleanup.sh
bash template_registry/cleanup.sh