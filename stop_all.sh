bash guardian/stop_services.sh
bash pdo_client/webapp/cleanup.sh --scratch /tmp/pdo_scratch

docker ps -q --filter ancestor=mlcommons/pdo_toy_asset_registry:latest | xargs -r docker stop
docker ps -q --filter ancestor=mlcommons/pdo_toy_template_registry:latest | xargs -r docker stop
docker ps -q --filter ancestor=mlcommons/pdo_ledger:latest | xargs -r docker stop
docker ps -q --filter ancestor=mlcommons/pdo_services:latest | xargs -r docker stop