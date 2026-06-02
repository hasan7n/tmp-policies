: "${ASSET_REGISTRY_IMAGE?Missing environment variable ASSET_REGISTRY_IMAGE}"
: "${CONTAINER_NETWORK_INTERFACE?Missing environment variable CONTAINER_NETWORK_INTERFACE}"
: "${ASSET_REGISTRY_PORT?Missing environment variable ASSET_REGISTRY_PORT}"

docker run --rm --user "$(id -u):0" --name asset_registry_container \
    -p $CONTAINER_NETWORK_INTERFACE:$ASSET_REGISTRY_PORT:8000 $ASSET_REGISTRY_IMAGE
    