MY_HOST=$(hostname -I | awk '{print $1}')

# build policy client docker image
bash pdo_client/build.sh \
    --image mlcommons/pdo_base_client:latest \
    --repository https://github.com/hasan7n/pdo-contracts \
    --branch poc \
    --families "exchange-contract identity-contract download-contract"

# build guardian docker image
bash guardian/build.sh \
    --image mlcommons/toy_guardian:latest \
    --client-image mlcommons/pdo_base_client:latest


# run policy client cli test
bash pdo_client/docker/run_cli.sh \
    --image mlcommons/pdo_base_client:latest \
    --cert-path /tmp/pdo_ledger/ccf/keys/networkcert.pem \
    --site-toml /tmp/pdo_services/services/etc/site.toml \
    --host $MY_HOST \
    --ledger-url http://$MY_HOST:6600 \
    --eservice-url random

# generate user keys for python test
mkdir -p /tmp/pdo_keys
bash docker_generate_user_keys.sh \
    --keys-folder /tmp/pdo_keys \
    --image mlcommons/pdo_base_client:latest \
    --users "user1 user2 user3 user4 user5 data_owner data_user vc"

# run policy client python test
bash pdo_client/docker/run_python.sh \
    --image mlcommons/pdo_base_client:latest \
    --cert-path /tmp/pdo_ledger/ccf/keys/networkcert.pem \
    --site-toml /tmp/pdo_services/services/etc/site.toml \
    --host $MY_HOST \
    --ledger-url http://$MY_HOST:6600 \
    --guardian-url http://$MY_HOST:7900 \
    --keys-folder /tmp/pdo_keys

# run policy client webapp (bare metal)
bash pdo_client/webapp/cleanup.sh --scratch /tmp/pdo_scratch
export PDO_INSTALL_ROOT=/home/hasan/work/pdos/pdo_install
export PDO_CONTRACTS_ROOT=/home/hasan/work/pdos/pdo_contracts
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