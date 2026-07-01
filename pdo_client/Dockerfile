FROM ubuntu:22.04

ARG REPOSITORY
ARG BRANCH
ARG CONTRACT_FAMILIES

ENV DEBIAN_FRONTEND=noninteractive
# Only the two roots are env (every other setup input is a script arg).
ENV PDO_CONTRACTS_ROOT=/pdo-contracts
ENV PDO_INSTALL_ROOT=/pdo_install

WORKDIR /

# Copy the build inputs and do the heavy build first. setup/ holds the install
# steps and activate_env.sh (sourced both at build time and at runtime by the
# runners), so it stays in the image. The runtime scripts are copied last
# (below) so editing them does not invalidate these cached build layers.
COPY setup/ /setup/

RUN bash /setup/install_system_deps.sh
RUN bash /setup/clone_contracts.sh --repository "${REPOSITORY}" --branch "${BRANCH}"
RUN bash /setup/install_pdo_client.sh
RUN bash /setup/install_contracts.sh --families "${CONTRACT_FAMILIES}"

RUN rm -rf ${PDO_INSTALL_ROOT}/opt/pdo/keys/*

# Webapp dependencies, installed into the PDO client virtualenv. requirements
# are copied alone so editing the webapp source does not bust this pip layer.
COPY webapp/requirements.txt /tmp/webapp-requirements.txt
RUN ${PDO_INSTALL_ROOT}/bin/pip install -r /tmp/webapp-requirements.txt

# Runtime code last: editing it only rebuilds from these layers down.
COPY scripts/ /scripts/
COPY webapp/ /webapp/

# Non-root user + group 0 access on the build outputs and runtime code so any
# host uid can read/write mounted volumes when launched with `--user $(id -u):0`.
# New files written at runtime inherit gid 0 from the process's egid.
RUN useradd -m -u 1000 pdo_user && \
    chgrp -R 0 ${PDO_INSTALL_ROOT}/opt/pdo ${PDO_CONTRACTS_ROOT}/rego-contract/test /scripts /webapp && \
    chmod -R g=u ${PDO_INSTALL_ROOT}/opt/pdo ${PDO_CONTRACTS_ROOT}/rego-contract/test /scripts /webapp

USER 1000:0

# bash is the entrypoint; CMD is the runner (+ args) to execute. The default
# runs the CLI test. run_python.sh overrides the CMD with run_python.sh, and
# the webapp's run_docker.sh overrides it with /webapp/run.sh.
ENTRYPOINT ["bash"]
CMD ["/scripts/run_cli.sh"]
