"""Example webapp seed.

Runs a small end-to-end download-contract flow before the dev server starts,
so the webapp comes up with wallets, credentials, and an exposed asset already
in place. Three users take part:

    vc_issuer   creates a wallet and a "poc" signing context, then issues three
                verifiable credentials (consent / membership / public key).
    data_user   creates a wallet and stores those three credentials.
    data_owner  registers an asset ("data1") and exposes it behind a download
                policy.

It goes through the webapp's own helpers (`runner` = app.pdo_runner) and the
asset/template registries (`registry_client`), so everything shows up in the
UI exactly as if it had been done by hand.

Pass it at launch:

    ./run.sh ... --seed seeds/example_seed.py             # bare metal
    docker/run_webapp.sh ... --seed seeds/example_seed.py # docker

`manage.py seed` injects these globals (no runtime import needed): `state`,
`bindings`, `runner` (app.pdo_runner), `settings`. The `TYPE_CHECKING` import
below is only so VS Code / Pylance shows signatures and autocomplete for them;
it is skipped at runtime.

Each user name must match a key copied into PDO_HOME/keys by bootstrap (i.e. a
key in the --keys-folder). Exposing the asset additionally needs the asset
registry and a guardian running.
"""

import time
from typing import TYPE_CHECKING

from app import registry_client
from app.did_utils import make_did
from app.models import AppConfig

if TYPE_CHECKING:
    from seed_context import bindings, runner, settings, state  # noqa: F401

# -----------------------------------------------------------------
# Participants and fixtures
# -----------------------------------------------------------------
VC_ISSUER = "vc_issuer"
DATA_OWNER = "data_owner"
DATA_USER = "data_user"

SIGNING_CONTEXT = "poc"

GUARDIAN_HOST = "192.168.1.223"
GUARDIAN_PORT = "7900"

PUBLIC_KEY = (
    "-----BEGIN PUBLIC KEY-----\n"
    "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAm/3dUBiOnAyZyJ7ZfZOQ\n"
    "L965qtOthxA+AmRQVNE1Qr9Y39zjT8U7FKG9UAbWLsZbIUct6qHDPfr6tbeSFPKc\n"
    "Bj0u5bCoI3tdvcN7fr1acJnZsrR1Yk5xkV6UKANJbC3kUAIHDg8kDM8R9mlsxBmu\n"
    "qpeF1ySuF1Awfw0FH/7hNi2ZyHVlxku3Z4CG3xEtHj8pNb+PT7jFTjfBtvwRLOz+\n"
    "B7OJUPpkyG9Hrc1Ulc9y+qZXOSwG+IJqsS4574U6VPdfpzrjBNLdtiUulUSx+M2I\n"
    "vwA3YYPAq+BVcOXCJ5/51v0lu5kb2soA6ZJ8IRU+WQwzFkT5PN43fGu69B5S+vcR\n"
    "5wIDAQAB\n"
    "-----END PUBLIC KEY-----\n"
)


def login(user_name):
    """Configure the webapp identity so the UI lists this user's contracts."""
    config = AppConfig.get_instance()
    config.public_key = user_name
    config.save()
    print(f"Configured webapp identity: {user_name}")


def issue_vc(issuer_wallet, subject_wallet, vc_type, claims):
    """vc_issuer signs a `vc_type` credential for `subject_wallet`.

    Mirrors the webapp's WalletSignCredential endpoint: the credential is
    issued from the "poc" signing context and bound to the subject's DID.
    """
    credential = {
        "type": [vc_type],
        "issuer": {"id": make_did(issuer_wallet, SIGNING_CONTEXT)},
        "credentialSubject": {
            "subject": {"id": make_did(subject_wallet)},
            "claims": claims,
        },
    }
    return runner.sign_credential(
        issuer_wallet,
        signing_context_path=[SIGNING_CONTEXT],
        credential_dict=credential,
        user_name=VC_ISSUER,
    )


# -----------------------------------------------------------------
# vc_issuer: wallet + "poc" signing context
# -----------------------------------------------------------------
issuer_wallet = runner.create_wallet("issuer wallet", VC_ISSUER)
print(f"[vc_issuer] wallet: {issuer_wallet}")
time.sleep(1)
runner.register_signing_context(
    issuer_wallet,
    VC_ISSUER,
    path=[SIGNING_CONTEXT],
    description="poc issuer",
)
print(f'[vc_issuer] registered signing context "{SIGNING_CONTEXT}"')

# -----------------------------------------------------------------
# data_user: wallet
# -----------------------------------------------------------------
user_wallet = runner.create_wallet("user wallet", DATA_USER)
print(f"[data_user] wallet: {user_wallet}")
time.sleep(1)

# -----------------------------------------------------------------
# vc_issuer -> data_user: consent, membership, and public-key VCs
# -----------------------------------------------------------------
signed_vcs = {
    "consent": issue_vc(issuer_wallet, user_wallet, "consent", {"document": "did:1234"}),
    "membership": issue_vc(issuer_wallet, user_wallet, "membership", {"member_of": "abc"}),
    "public_key": issue_vc(issuer_wallet, user_wallet, "public_key", {"key": PUBLIC_KEY}),
}
for vc_type in signed_vcs:
    print(f"[vc_issuer] issued {vc_type} VC")

# data_user stores each credential in their wallet.
for vc_type, vc in signed_vcs.items():
    runner.wallet_add_vc(user_wallet, vc, DATA_USER)
    print(f"[data_user] stored {vc_type} VC")

# -----------------------------------------------------------------
# data_owner: register asset "data1"
# -----------------------------------------------------------------
asset_contract_id = runner.create_wallet("data1", DATA_OWNER)
asset_did = make_did(asset_contract_id)
registry_asset = registry_client.register_asset(
    name="data1",
    did=asset_did,
    metadata={
        "guardian_url": GUARDIAN_HOST,
        "guardian_port": GUARDIAN_PORT,
        "data_source": "/path",
    },
)
registry_pk = registry_asset["id"]
registry_client.update_asset_metadata(
    registry_pk,
    {
        "asset_registry_url": (
            f"{settings.ASSET_REGISTRY_URL.rstrip('/')}/api/assets/{registry_pk}/"
        )
    },
)
print(f"[data_owner] registered asset data1: {asset_did}")

# -----------------------------------------------------------------
# data_owner: expose the asset behind a download policy
# -----------------------------------------------------------------
guardian = f"http://{GUARDIAN_HOST}:{GUARDIAN_PORT}"
policy = runner.create_asset_policy("Policy for data1", guardian, DATA_OWNER)
policy_data = {
    "allowed_institutions": ["abc", "mlcommons"],
    "consent_document": "did:1234",
}
runner.set_policy_data(policy["policy_contract_id"], policy_data, DATA_OWNER)
registry_client.update_asset_metadata_by_did(
    asset_did,
    {
        "policy_contract": make_did(policy["token_contract_id"]),
        "policy_data": policy_data,
    },
)
print(f"[data_owner] exposed data1 (token {policy['token_contract_id']})")

# Land the webapp on the data_user identity (change to whichever user you want
# the browser session to start as).
login(DATA_USER)
print("Seed complete.")
