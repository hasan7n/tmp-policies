FROM ubuntu:22.04

ARG REPOSITORY
ARG BRANCH
ARG CONTRACT_FAMILIES

ENV DEBIAN_FRONTEND=noninteractive
# Only the two roots are env (every other setup input is a script arg).
ENV PDO_CONTRACTS_ROOT=/pdo-contracts
ENV PDO_INSTALL_ROOT=/pdo_install

WORKDIR /

# Reuse the same scripts the host flow uses (build context is the pdo_client_v2
# folder, see build.sh). The runners live in scripts/ alongside the shared
# scripts they source, so the container resolves them exactly as the host does.
# setup/ is only needed at build time.
COPY scripts/ /scripts/
COPY setup/ /setup/

RUN bash /setup/install_system_deps.sh
RUN bash /setup/clone_contracts.sh --repository "${REPOSITORY}" --branch "${BRANCH}"
RUN bash /setup/install_pdo_client.sh
RUN bash /setup/install_contracts.sh --families "${CONTRACT_FAMILIES}"

RUN rm -rf ${PDO_INSTALL_ROOT}/opt/pdo/keys/*

# Non-root user + group 0 access so any host uid can read/write mounted
# volumes when launched with `--user $(id -u):0`. New files written at
# runtime inherit gid 0 from the process's egid.
RUN useradd -m -u 1000 pdo_user && \
    chgrp -R 0 ${PDO_INSTALL_ROOT}/opt/pdo ${PDO_CONTRACTS_ROOT}/download-contract/test /scripts && \
    chmod -R g=u ${PDO_INSTALL_ROOT}/opt/pdo ${PDO_CONTRACTS_ROOT}/download-contract/test /scripts
USER 1000:0

# bash is the entrypoint; CMD is the runner (+ args) to execute. The default
# runs the CLI test; run_python.sh just overrides the CMD with run_python.sh.
ENTRYPOINT ["bash"]
CMD ["/scripts/run_cli.sh"]
