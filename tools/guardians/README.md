# guardians

One folder per guardian type. An asset picks one when it is registered.

| Folder        | What it does                                                          |
|---------------|-----------------------------------------------------------------------|
| `public/`     | serves the data to any caller, unauthenticated; no policy at all      |
| `download/`   | `do_download` releases the data encrypted to the requester's key      |
| `inference/`  | `do_inference` plus the FL client that redeems it; the data stays put |

## The contract with the webapp

The webapp is told one path — `GUARDIANS_DIR`, this folder — and discovers what is
in it. A guardian is any subfolder holding both a `run.sh` and a `guardian.json`:

```json
{
  "type": "download",
  "title": "Download",
  "description": "Releases the data encrypted to the requester's session key.",
  "order": 20,
  "image": { "env": "GUARDIAN_IMAGE", "default": "mlcommons/toy_guardian:latest" },
  "options": {
    "--image": "image",
    "--interface": "bind_interface",
    "--port": "port",
    "--data-path": "data_path"
  }
}
```

| Field         | Meaning                                                              |
|---------------|----------------------------------------------------------------------|
| `type`        | the identifier recorded on the asset and used everywhere else        |
| `title`       | short label for the registration form                                |
| `description` | one line shown under the guardian picker                             |
| `order`       | sort position in the form (default 100)                              |
| `image`       | optional Docker image, with the env var that overrides it            |
| `options`     | the `run.sh` options this guardian takes, in the order to pass them  |

`options` maps an option to the *name of a value*, not a value. The webapp computes
every value a launch could need and each guardian names the ones its `run.sh`
actually takes:

| Value              | What it is                                             |
|--------------------|--------------------------------------------------------|
| `data_path`        | host path of the file the guardian serves              |
| `bind_interface`   | interface to listen on                                 |
| `advertised_host`  | host others use to reach it                            |
| `port`             | port to publish                                        |
| `storage_port`     | the paired PDO storage service port (`port` + 1)       |
| `image`            | the image resolved from the `image` block              |
| `fl_server_url`    | FL server, as addressable from inside the guardian     |

A guardian needing something outside this vocabulary also needs a new entry in
`LAUNCH_VALUES` in `pdo_client/webapp/app/guardian_registry.py`.

Every guardian must answer `GET /info` with a 200 once it is up; that is the
readiness check, and the only endpoint they all share.

## Adding a guardian

1. Create a folder here with a `run.sh` and a `guardian.json`.
2. Add a runner to `pdo_client/webapp/app/action_runners.py` keyed by the same
   `type`.

Step 2 is not configuration: how a consumer drives a guardian — what it collects,
what it does with the capability, what comes back — is behaviour, and lives in
code. A guardian with a manifest but no runner is launchable but not usable, so the
registration form does not offer it.
