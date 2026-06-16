bash asset_registry/build.sh \
    --image mlcommons/pdo_toy_asset_registry:latest

bash template_registry/build.sh \
    --image mlcommons/pdo_toy_template_registry:latest

bash pdo_client/build.sh \
    --image mlcommons/pdo_base_client:latest \
    --repository https://github.com/hasan7n/pdo-contracts \
    --branch poc \
    --families "exchange-contract identity-contract download-contract"

bash guardian/build.sh \
    --image mlcommons/toy_guardian:latest \
    --client-image mlcommons/pdo_base_client:latest

bash policy_engine/build.sh \
    --ledger-image mlcommons/pdo_ledger:latest \
    --services-image mlcommons/pdo_services:latest \
    --repository https://github.com/hasan7n/pdo-contracts \
    --branch poc