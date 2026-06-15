# client app

A local webapp for PDO interactions.

## Configuration

Configuration lives in a `.env` file (loaded by `config/settings.py` via
`django-environ`). Copy the template and fill it in:

```
cp .env.example .env
```

- **Service URLs** (`LEDGER_URL`, `ASSET_REGISTRY_URL`, `TEMPLATE_REGISTRY_URL`)
  and the **PDO connection** vars are read from `.env`. They are no longer
  editable in the UI — the config page shows them read-only.
- The only user-editable setting is the **public key / identity**, stored in
  the database.

In the Docker image, `PDO_INSTALL_ROOT` and the input-file paths
(`LEDGER_CERT_PATH`, `SITE_TOML_SOURCE`, `USER_KEYS_FOLDER`) are fixed by the
Dockerfile and the bind mounts, so a `.env` used for Docker only needs the
service URLs and PDO connection settings.

## Local run

```
./run.sh --interface 127.0.0.1 --port 8000
```

## Docker

```
./build.sh --client-image <pdo-client-image> [--image <tag>]

./run_docker.sh \
    --image <tag> \
    --interface 0.0.0.0 --port 8000 \
    --cert-path /path/to/networkcert.pem \
    --site-toml /path/to/site.toml \
    --keys-folder /path/to/user_keys
```

## Cleanup

```
./cleanup.sh
```
