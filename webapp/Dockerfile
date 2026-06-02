ARG PDO_CLIENT_IMAGE
FROM $PDO_CLIENT_IMAGE

USER root
COPY ./requirements.txt /tmp/requirements.txt

# Webapp setup
RUN ${PDO_INSTALL_ROOT}/bin/pip install -r /tmp/requirements.txt

COPY . /webapp
RUN chgrp -R 0 /webapp && \
    chmod -R g=u /webapp
USER 1000:0

ENTRYPOINT [ "bash", "-c", "source ${PDO_INSTALL_ROOT}/bin/activate && cd /webapp && bash run.sh" ]
