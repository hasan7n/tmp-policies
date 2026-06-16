mkdir -p /tmp/pdo_keys
bash docker_generate_user_keys.sh \
    --keys-folder /tmp/pdo_keys \
    --image mlcommons/pdo_base_client:latest \
    --users "user1 user2 user3 user4 user5 data_owner data_user vc"

bash docker_start_policy_engine.sh
bash docker_start_guardian.sh
bash docker_start_registries.sh
bash docker_start_webapp.sh
