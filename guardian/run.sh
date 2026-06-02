: "${F_GUARDIAN_HOST?Missing environment variable F_GUARDIAN_HOST}"
docker run --rm --env F_GUARDIAN_HOST=$F_GUARDIAN_HOST \
    --network=host --name pdo-guardian pdo-guardian:latest