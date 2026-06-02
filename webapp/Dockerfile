FROM pdo_policies:latest

COPY ./requirements.txt /tmp/requirements.txt

# Webapp setup
RUN ${PDO_INSTALL_ROOT}/bin/pip install -r /tmp/requirements.txt

COPY . /webapp

ENTRYPOINT [ "bash", "-c", "source ${PDO_INSTALL_ROOT}/bin/activate && cd /webapp && bash run.sh" ]
