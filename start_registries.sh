set -e
cd asset_registry && bash run.sh -n 127.0.0.1 -p 8001 &
cd template_registry && bash run.sh -n 127.0.0.1 -p 8002 &
