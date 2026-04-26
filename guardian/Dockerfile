FROM pdo_contracts:0.4.29

# Install guardian operation dependencies
COPY requirements.txt /project/requirements.txt
RUN bash -c 'source ~/tools/environment.sh && ${PDO_INSTALL_ROOT}/bin/pip install -r /project/requirements.txt'

# Install guardian operation as a module
COPY --chown=${UNAME}:${UNAME} . /project/my_guardian
RUN bash -c 'source ~/tools/environment.sh && ${PDO_INSTALL_ROOT}/bin/pip install -e /project/my_guardian'

# Configure guardian service to use the new operation
RUN bash -c 'source ~/tools/environment.sh && sed -i "s|^## Operations = '\''pdo.common.operations'\''|Operations = '\''guardian_operation'\''|" ${PDO_HOME}/etc/contracts/guardian_service.toml'

ENTRYPOINT [ "bash", "/project/my_guardian/start_services.sh" ]
