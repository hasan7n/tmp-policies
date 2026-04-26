FROM pdo_contracts:0.4.29

RUN echo "SET(CONTRACT_FAMILIES exchange-contract identity-contract download-contract)" > $PDO_CONTRACTS_ROOT/Local.cmake
COPY ./policies/download-contract $PDO_CONTRACTS_ROOT/download-contract

RUN bash -c 'source ${PDO_INSTALL_ROOT}/bin/activate && source ${PDO_SOURCE_ROOT}/build/common-config.sh && make -C ${PDO_CONTRACTS_ROOT}'
RUN bash -c 'source ${PDO_INSTALL_ROOT}/bin/activate && source ${PDO_SOURCE_ROOT}/build/common-config.sh && make -C ${PDO_CONTRACTS_ROOT} install'

COPY ./entrypoint.sh /project/entrypoint.sh

ENTRYPOINT [ "bash", "/project/entrypoint.sh" ]