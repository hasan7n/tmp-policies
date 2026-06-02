set -e
cd asset_registry && bash run.sh &
cd template_registry && bash run.sh &
cd client_app && bash run.sh &