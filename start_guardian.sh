set -e
MY_HOST="$(hostname -I | awk '{print $1}')"

export INTERFACE=$MY_HOST
export F_GUARDIAN_HOST=$MY_HOST
export PDO_INSTALL_ROOT=/home/hasan/work/pdos/pdo_install
export PDO_CONTRACTS_ROOT=/home/hasan/work/pdos/pdo-contracts
export GUARDIAN_DATA_PATH=/home/hasan/work/pdos/tmp-policies/README.md
bash guardian/stop_services.sh
bash guardian/start_services.sh &