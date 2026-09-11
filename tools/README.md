# Policy Fabric

## Components

| Folder                | What it is                                                            |
|-----------------------|-----------------------------------------------------------------------|
| `pdo_client/`         | the webapp and the PDO client it drives                               |
| `asset_registry/`     | toy asset registry                                                    |
| `template_registry/`  | toy policy card and credential schema registry                        |
| `policy_engine/`      | ledger and PDO services                                               |
| `guardians/`          | the guardians an asset can be put behind; see its own README          |
| `fl_server/`          | toy FL server the webapp submits inference jobs to                    |
| `tests/`              | the tutorials, driven through a browser; see its own README           |

## Setup

Build the policy_engine, guardians, and pdo_contract_base — `docker_build_all.sh`
does all of it, and names the pdo-contracts revision and the image tag in one
place at the top.

## Test

1. Run the ledger
2. Run the pdo services
3. Start a data guardian
4. generate user keys
5. Start the policies client

For the inference flow, also start the FL server (`start_fl_server.sh`) before
registering an asset behind an inference guardian: the webapp submits jobs to it
and the FL client bundled with each inference guardian polls it for them.

`make_tutorial_files.sh` writes the files both tutorials register as assets, and
prints the script digest the inference tutorial asks for.

`tests/run_webui_inference_test.sh` does the whole of the above and then drives
the inference tutorial through a browser, recording it.
