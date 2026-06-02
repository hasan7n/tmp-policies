: "${TEMPLATE_REGISTRY_IMAGE?Missing environment variable TEMPLATE_REGISTRY_IMAGE}"
: "${CONTAINER_NETWORK_INTERFACE?Missing environment variable CONTAINER_NETWORK_INTERFACE}"
: "${TEMPLATE_REGISTRY_PORT?Missing environment variable TEMPLATE_REGISTRY_PORT}"

docker run --rm --name template_registry_container --user "$(id -u):0" \
    -p $CONTAINER_NETWORK_INTERFACE:$TEMPLATE_REGISTRY_PORT:8000 $TEMPLATE_REGISTRY_IMAGE