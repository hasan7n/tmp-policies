rm -rf /tmp/pdo_scratch
mkdir -p /tmp/pdo_scratch

INTERFACE="$(hostname -I | awk '{print $1}')"
bash pdo_client/docker/run_webapp.sh \
    --image mlcommons/pdo_base_client:latest \
    --interface $INTERFACE \
    --port 8000 \
    --cert-path /tmp/pdo_ledger/ccf/keys/networkcert.pem \
    --site-toml /tmp/pdo_services/services/etc/site.toml \
    --keys-folder /tmp/pdo_keys \
    --scratch /tmp/pdo_scratch \
    --ledger-url http://$INTERFACE:6600 \
    --service-host $INTERFACE \
    --asset-registry-url http://$INTERFACE:8001 \
    --template-registry-url http://$INTERFACE:8002