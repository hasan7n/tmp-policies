: "${PDO_CLIENT_IMAGE?Missing environment variable PDO_CLIENT_IMAGE}"

docker build -t $PDO_CLIENT_IMAGE -f ./Dockerfile .