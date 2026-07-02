# run policy client webapp (bare metal)
export PDO_INSTALL_ROOT=/home/hasan/work/pdos/pdo_install
export PDO_CONTRACTS_ROOT=/home/hasan/work/pdos/pdo-contracts

MY_HOST="$(hostname -I | awk '{print $1}')"
# bash pdo_client/scripts/run_cli.sh \
#     --cert-path /tmp/pdo_ledger/ccf/keys/networkcert.pem \
#     --site-toml /tmp/pdo_services/services/etc/site.toml \
#     --host $MY_HOST \
#     --ledger-url http://$MY_HOST:6600

bash pdo_client/scripts/run_python.sh \
    --cert-path /tmp/pdo_ledger/ccf/keys/networkcert.pem \
    --site-toml /tmp/pdo_services/services/etc/site.toml \
    --host $MY_HOST \
    --ledger-url http://$MY_HOST:6600 \
    --guardian-url http://$MY_HOST:7900 \
    --keys-folder /tmp/pdo_keys

