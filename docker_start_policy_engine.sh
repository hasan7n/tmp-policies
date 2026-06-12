set -e
INTERFACE="$(hostname -I | awk '{print $1}')"
cd pdo_images && bash run_ledger.sh -i "mlcommons/pdo_ledger:latest" -n $INTERFACE -p "6600" &
sleep 10
cd pdo_images && bash run_services.sh -l http://$INTERFACE:6600 -i "mlcommons/pdo_services:latest" -n $INTERFACE &
sleep 15
