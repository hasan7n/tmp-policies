ESERVICE=1
docker exec services_container bash -c "cat /project/pdo/run/opt/pdo/logs/eservice${ESERVICE}.log"
# docker exec services_container bash -c "ls /project/pdo/run/opt"