ARG PDO_CLIENT_IMAGE
FROM $PDO_CLIENT_IMAGE

USER root
COPY ./requirements.txt /tmp/requirements.txt

# Webapp setup
RUN ${PDO_INSTALL_ROOT}/bin/pip install -r /tmp/requirements.txt

# Put the PDO client virtualenv on PATH so `python` in run.sh resolves to it
# (equivalent to sourcing ${PDO_INSTALL_ROOT}/bin/activate). All application
# configuration comes from the mounted .env, not from image env vars.
ENV PYTHONUNBUFFERED=1 \
    PATH=${PDO_INSTALL_ROOT}/bin:${PATH}

COPY . /webapp
WORKDIR /webapp
RUN chgrp -R 0 /webapp && \
    chmod -R g=u /webapp
USER 1000:0

# run.sh migrates, bootstraps the local PDO state, then execs the dev server.
# CMD holds the bind flags; override at runtime to change them.
ENTRYPOINT ["bash", "/webapp/run.sh"]
CMD ["--interface", "0.0.0.0", "--port", "8000"]
