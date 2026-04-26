LEDGER_WS=/tmp/ledger_ws
LEDGER_WS=/home/hasan/work/pdos/pdo-contracts/docker/xfer

docker run --cap-add=SYS_PTRACE --security-opt seccomp=unconfined --rm --network host --name policies_client_container \
    --volume ${LEDGER_WS}:/tmp/ledger_ws \
    -it --entrypoint bash \
    pdo_policies:latest