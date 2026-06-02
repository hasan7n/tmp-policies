: "${PDO_CLIENT_IMAGE?Missing environment variable PDO_CLIENT_IMAGE}"
: "${GUARDIAN_IMAGE?Missing environment variable GUARDIAN_IMAGE}"

docker build --build-arg PDO_CLIENT_IMAGE=$PDO_CLIENT_IMAGE -f Dockerfile -t $GUARDIAN_IMAGE .