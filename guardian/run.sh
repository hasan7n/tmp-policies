: "${GUARDIAN_IMAGE?Missing environment variable GUARDIAN_IMAGE}"
: "${CONTAINER_NETWORK_INTERFACE?Missing environment variable CONTAINER_NETWORK_INTERFACE}"
: "${GUARDIAN_PORT?Missing environment variable GUARDIAN_PORT}"

docker run --rm --env F_GUARDIAN_HOST=0.0.0.0 --user "$(id -u):0" \
    -p $CONTAINER_NETWORK_INTERFACE:$GUARDIAN_PORT:7900 --name pdo-guardian $GUARDIAN_IMAGE