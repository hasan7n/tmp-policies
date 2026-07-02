# run policy client webapp (bare metal)
bash pdo_client/webapp/cleanup.sh --scratch /tmp/pdo_scratch
export PDO_INSTALL_ROOT=/home/hasan/work/pdos/pdo_install
export PDO_CONTRACTS_ROOT=/home/hasan/work/pdos/pdo-contracts

MY_HOST="$(hostname -I | awk '{print $1}')"
bash pdo_client/webapp/run.sh \
    --interface $MY_HOST \
    --port 8000 \
    --cert-path /tmp/pdo_ledger/ccf/keys/networkcert.pem \
    --site-toml /tmp/pdo_services/services/etc/site.toml \
    --keys-folder /tmp/pdo_keys \
    --scratch /tmp/pdo_scratch \
    --ledger-url http://$MY_HOST:6600 \
    --service-host $MY_HOST \
    --asset-registry-url http://$MY_HOST:8001 \
    --template-registry-url http://$MY_HOST:8002