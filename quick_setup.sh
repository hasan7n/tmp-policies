cd pdo_images && bash run_ledger.sh &
sleep 10
cd pdo_images && bash run_services.sh &
sleep 3
cd guardian && bash run.sh &
cd asset_registry && bash run.sh &
cd template_registry && bash run.sh &
cd client_app && bash run.sh &