set -e
cd pdo_images && bash run_ledger.sh &
sleep 10
cd pdo_images && bash run_services.sh &
sleep 15
