: "${TEMPLATE_REGISTRY_IMAGE?Missing environment variable TEMPLATE_REGISTRY_IMAGE}"

docker build -t $TEMPLATE_REGISTRY_IMAGE -f ./Dockerfile .