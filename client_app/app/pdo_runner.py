"""PDO operations using the decentralized helpers.

Wallets are signature_authority contracts. The ``identity`` python module is
used only for ``add_vc`` / ``get_vc_list`` / ``get_vp``, which are convenience
wrappers around contract methods that exist on signature_authority too.
Everything else goes through the ``signature_authority`` module.

Helpers mutate the shared state when loading contexts, so all calls run
under a single global lock.
"""

import json
import logging
import os
import tempfile
import threading
import time

# Importing pdo_config first ensures env vars are set before any pdo.* import.
from . import pdo_config as cfg  # noqa: F401  (side-effect import)

import pdo.identity.decentralized.signature_authority as signature_authority
import pdo.download.decentralized.policy_agent as policy_agent
import pdo.download.decentralized.download_token as download_token

from .pdo_state import get_state

logger = logging.getLogger(__name__)
_op_lock = threading.Lock()


def _tmp_json(data):
    fd, path = tempfile.mkstemp(prefix="pdo_op_", suffix=".json", dir=cfg.SCRATCH_DIR)
    with os.fdopen(fd, "w") as f:
        json.dump(data, f)
    return path


def _tmp_path(suffix):
    fd, path = tempfile.mkstemp(prefix="pdo_op_", suffix=suffix, dir=cfg.SCRATCH_DIR)
    os.close(fd)
    return path


def _safe_unlink(path):
    try:
        os.unlink(path)
    except OSError:
        pass


# ============================================================
# Wallet ops (signature_authority-backed)
# ============================================================
def create_wallet(name, user_name):
    """Create a wallet, backed by a signature_authority contract.

    Returns the contract_id.
    """
    state = get_state()
    with _op_lock:
        return signature_authority.create_signature_authority(
            state, user_name, description=f"wallet for {name}"
        )


def register_signing_context(
    contract_id, user_name, *, path, description, extensible=False
):
    """Register a new signing context (issuer) on a wallet's signature_authority."""
    state = get_state()
    with _op_lock:
        signature_authority.register_signing_context(
            state,
            contract_id,
            user_name,
            path=path,
            description=description,
            extensible=extensible,
        )


def wallet_add_vc(contract_id, vc_dict, user_name):
    """Add a verifiable credential to a wallet."""
    state = get_state()
    cred_path = _tmp_json(vc_dict)
    try:
        with _op_lock:
            signature_authority.add_vc(
                state, contract_id, user_name, credential_file=cred_path
            )
    finally:
        _safe_unlink(cred_path)


def wallet_list_vcs(contract_id, user_name):
    """Return the wallet's stored VCs as a dict (type → vc)."""
    state = get_state()
    with _op_lock:
        result = signature_authority.get_vc_list(state, contract_id, user_name)
    if isinstance(result, str):
        return json.loads(result) if result else {}
    return result or {}


def sign_credential(contract_id, signing_context_path, credential_dict, user_name):
    """Sign a credential with the given signing context path on a wallet.

    ``signing_context_path`` is a list of strings (e.g. ``["my_issuer"]``).
    Returns the signed VC dict.
    """
    state = get_state()
    cred_path = _tmp_json(credential_dict)
    signed_path = _tmp_path(".json")
    try:
        with _op_lock:
            signature_authority.sign_credential(
                state,
                contract_id,
                user_name,
                path=signing_context_path,
                credential=cred_path,
                signed_credential=signed_path,
            )
        with open(signed_path) as f:
            return json.load(f)
    finally:
        _safe_unlink(cred_path)
        _safe_unlink(signed_path)


# ============================================================
# Asset policy ops (owner-side)
# ============================================================
def create_asset_policy(description, guardian_url_port, user_name):
    """Create a policy agent + download token, then register the policy as
    a trusted issuer on the token.

    Returns ``{'policy_contract_id', 'token_contract_id'}``.
    """
    state = get_state()
    with _op_lock:
        policy_id = policy_agent.create_policy_agent(
            state, user_name, description=description
        )
        time.sleep(1)
        token_id = download_token.create_download_token(
            state, user_name, guardian_url_port
        )
        time.sleep(1)
        download_token.register_trusted_issuer(state, token_id, policy_id, user_name)
    return {"policy_contract_id": policy_id, "token_contract_id": token_id}


def set_policy_data(policy_id, policy_data, user_name):
    """Write the policy data dict into a policy agent contract."""
    state = get_state()
    data_path = _tmp_json(policy_data)
    try:
        with _op_lock:
            policy_agent.set_policy_data(state, policy_id, user_name, data=data_path)
    finally:
        _safe_unlink(data_path)


def register_policy_trusted_issuer(
    policy_id, issuer_id, user_name, *, path, credential_type
):
    """Register a signature authority as a trusted issuer on a policy agent
    for a given credential type at a given context path.
    """
    state = get_state()
    with _op_lock:
        policy_agent.register_trusted_issuer(
            state,
            policy_id,
            issuer_id,
            user_name,
            path=path,
            credential_type=credential_type,
        )


# ============================================================
# Asset use ops (consumer-side)
# ============================================================
def use_asset(*, wallet_id, token_id, guardian_url_port, user_name, output_dir=None):
    """Run the consumer download flow.

    1. Read the token's trusted-issuer list to discover the policy agent.
    2. Get credential requirements from the policy.
    3. Build a VP from the wallet covering those types.
    4. Issue a download credential from the policy.
    5. Download the (encrypted) data through the guardian.

    Returns ``(output_path, issued_vc_dict)``.
    """
    state = get_state()
    output_dir = output_dir or cfg.DOWNLOAD_OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)

    vp_path = _tmp_path(".json")
    issued_path = _tmp_path(".json")
    output_path = os.path.join(output_dir, f"download_{os.urandom(4).hex()}.bin")

    try:
        with _op_lock:
            issuers_raw = download_token.list_trusted_issuers(
                state, token_id, user_name
            )
            time.sleep(1)
            issuers = (
                json.loads(issuers_raw)
                if isinstance(issuers_raw, str)
                else (issuers_raw or {})
            )
            if not issuers:
                raise ValueError(
                    "No trusted issuers registered on this token contract."
                )
            policy_id = next(iter(issuers.keys()))

            creds_list = policy_agent.get_requirements(state, policy_id, user_name)
            time.sleep(1)
            signature_authority.get_vp(
                state,
                wallet_id,
                user_name,
                save_file="vp.json",
                types=creds_list,
                output_file=vp_path,
            )
            time.sleep(1)

            policy_agent.issue_policy_credential(
                state,
                policy_id,
                user_name,
                presentation=vp_path,
                issued_credential=issued_path,
            )
            time.sleep(1)
            download_token.do_download(
                state,
                token_id,
                user_name,
                guardian_url_port,
                vc_file=issued_path,
                output_file=output_path,
            )

        with open(issued_path) as f:
            issued_vc = json.load(f)
        return output_path, issued_vc
    finally:
        _safe_unlink(vp_path)
        _safe_unlink(issued_path)
