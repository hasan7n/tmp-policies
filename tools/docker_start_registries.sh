set -e
INTERFACE="$(hostname -I | awk '{print $1}')"
bash asset_registry/run_docker.sh \
    --image mlcommons/pdo_toy_asset_registry:latest \
    --interface $INTERFACE \
    --port 8001 &
bash template_registry/run_docker.sh \
    --image mlcommons/pdo_toy_template_registry:latest \
    --interface $INTERFACE \
    --port 8002 &
