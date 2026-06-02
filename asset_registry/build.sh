: "${ASSET_REGISTRY_IMAGE?Missing environment variable ASSET_REGISTRY_IMAGE}"

docker build -t $ASSET_REGISTRY_IMAGE -f ./Dockerfile .