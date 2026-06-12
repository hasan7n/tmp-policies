set -e
INTERFACE="$(hostname -I | awk '{print $1}')"
cd asset_registry && bash run_docker.sh -i mlcommons/pdo_toy_asset_registry:latest -n $INTERFACE -p 8001 &
cd template_registry && bash run_docker.sh -i mlcommons/pdo_toy_template_registry:latest -n $INTERFACE -p 8002 &
