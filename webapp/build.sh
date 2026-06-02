: "${WEBAPP_IMAGE?Missing environment variable WEBAPP_IMAGE}"
: "${PDO_CLIENT_IMAGE?Missing environment variable PDO_CLIENT_IMAGE}"

docker build --build-arg PDO_CLIENT_IMAGE=$PDO_CLIENT_IMAGE -t $WEBAPP_IMAGE -f ./Dockerfile .