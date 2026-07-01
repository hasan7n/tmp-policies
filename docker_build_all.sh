set -e

BRANCH=a3d3c04cfcf2330268145c73732df88a1d439183

bash asset_registry/build.sh \
    --image mlcommons/pdo_toy_asset_registry:latest

bash template_registry/build.sh \
    --image mlcommons/pdo_toy_template_registry:latest

bash pdo_client/build.sh \
    --image mlcommons/pdo_base_client:latest \
    --repository https://github.com/hasan7n/pdo-contracts \
    --branch $BRANCH \
    --families "exchange-contract identity-contract rego-contract"

bash guardian/build.sh \
    --image mlcommons/toy_guardian:latest \
    --client-image mlcommons/pdo_base_client:latest

bash policy_engine/build_pdo_images.sh \
    --ledger-image mlcommons/pdo_ledger:latest \
    --services-image mlcommons/pdo_services:latest \
    --repository https://github.com/hasan7n/pdo-contracts \
    --branch $BRANCH

docker push mlcommons/pdo_toy_asset_registry:latest
docker push mlcommons/pdo_toy_template_registry:latest
docker push mlcommons/pdo_base_client:latest
docker push mlcommons/toy_guardian:latest
docker push mlcommons/pdo_ledger:latest
docker push mlcommons/pdo_services:latest