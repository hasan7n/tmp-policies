"""PDO operations using the decentralized helpers.

Wallets are ``identity.identity`` contracts. Asset identities and "manual"
issuers are ``signature_authority`` contracts (a superset: it inherits
identity's ops and adds signing-context issuance). The op classes behind
``add_vc`` / ``get_vc_list`` / ``get_vp`` / ``register_signing_context`` /
``list_signing_contexts`` are literally the same across ``identity``,
``signature_authority``, and ``external_key_authority`` (each family aliases
the one below it), so the ``signature_authority`` decentralized module below
is used as the one family-agnostic entry point for all of them by contract_id
— only ``sign_credential`` is NOT reusable against an ``external_key_authority``
contract (it's a distinct, non-aliased op there).

Helpers mutate the shared state when loading contexts, so all calls run
under a single global lock.
"""

import json
import logging
import os
import tempfile
import threading
import time

# settings (loaded during django.setup()) prepares the PDO environment.
# Read it before importing pdo.* so the env vars are already set.
from django.conf import settings as cfg

_ = cfg.PDO_HOME  # force settings to load (and set os.environ) before pdo.*

import pdo.authority.decentralized.external_key_authority as external_key_authority
import pdo.identity.decentralized.identity as identity_contract
import pdo.identity.decentralized.signature_authority as signature_authority
import pdo.rego.decentralized.rego_policy_agent as rego_policy_agent
import pdo.rego.decentralized.rego_token as rego_token

from .pdo_state import get_state

logger = logging.getLogger(__name__)
_op_lock = threading.Lock()

PUBLIC_KEY_CREDENTIAL_TYPE = "publicKeyCredential"


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
# Wallet ops (identity.identity-backed)
# ============================================================
def create_wallet(name, user_name):
    """Create a wallet, backed by a plain identity.identity contract.

    Returns the contract_id.
    """
    state = get_state()
    with _op_lock:
        return identity_contract.create_identity(
            state, user_name, description=f"wallet for {name}"
        )


# ============================================================
# Identity ops shared by asset identities and issuers
# (signature_authority-backed; see the module docstring for why this one
# decentralized module is reused as the family-agnostic entry point)
# ============================================================
def create_asset_identity(name, user_name):
    """Create the identity contract behind an asset, backed by
    signature_authority (unlike a wallet, this is not a user-facing "wallet").

    Returns the contract_id.
    """
    state = get_state()
    with _op_lock:
        return signature_authority.create_signature_authority(
            state, user_name, description=f"asset identity for {name}"
        )


def create_manual_issuer(name, user_name):
    """Create a "manual" issuer: a signature_authority contract the owner
    registers signing contexts on and hand-signs credentials from.

    Returns the contract_id.
    """
    state = get_state()
    with _op_lock:
        return signature_authority.create_signature_authority(
            state, user_name, description=f"issuer for {name}"
        )


def create_external_key_authority_issuer(name, user_name):
    """Create an external_key_authority issuer. This single call also
    creates and trusts its backing wallet_key_authority (see
    ``cmd_create_external_key_authority``).

    Unlike ``create_signature_authority``, ``cmd_create_external_key_authority``
    takes no ``description`` argument — the eka's (and its wka's) description
    comes fixed from their context templates, so ``name`` is accepted here only
    for call-site symmetry with the other ``create_*`` functions and isn't
    otherwise used.

    Returns the contract_id.
    """
    state = get_state()
    with _op_lock:
        return external_key_authority.create_external_key_authority(state, user_name)


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


def wallet_list_signing_contexts(contract_id, user_name, path=None):
    """Return the wallet's registered signing contexts as a list.

    Each entry is ``{"path": [..], "description": "..", "extensible": bool}``.
    """
    state = get_state()
    with _op_lock:
        raw = signature_authority.list_signing_contexts(
            state, contract_id, user_name, path=path or [],
        )
    if isinstance(raw, str):
        parsed = json.loads(raw) if raw else {}
    else:
        parsed = raw or {}
    return parsed.get("contexts", []) if isinstance(parsed, dict) else []


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
def create_asset_policy(description, guardian_url_port, user_name, rego_modules):
    """Create a rego_policy_agent + rego_token, provision the chosen Rego
    subpolicies, and register the policy as a trusted issuer on the token.

    ``rego_modules`` is a list of ``[subpolicy_id, rego_source]`` pairs (the
    policies the owner selected). ``cmd_set_rego_policy`` reads each module from
    a file, so each source is materialized to a temp file first.

    Returns ``{'policy_contract_id', 'token_contract_id'}``.
    """
    state = get_state()

    # materialize the selected subpolicies as files (cmd_set_rego_policy reads paths)
    module_paths = []
    module_args = []
    for subpolicy_id, source in rego_modules:
        path = _tmp_path(".rego")
        with open(path, "w") as f:
            f.write(source)
        module_paths.append(path)
        module_args.append([subpolicy_id, path])

    try:
        with _op_lock:
            policy_id = rego_policy_agent.create_rego_policy_agent(
                state, user_name, description=description
            )
            time.sleep(1)
            rego_policy_agent.set_rego_policy(
                state, policy_id, user_name, module=module_args
            )
            time.sleep(1)
            token_id = rego_token.create_rego_token(
                state, user_name, guardian_url_port
            )
            time.sleep(1)
            rego_token.register_trusted_issuer(
                state,
                token_id,
                policy_id,
                user_name,
                credential_types=["policy_decision"],
                path=["__ISSUER__"],
            )
    finally:
        for path in module_paths:
            _safe_unlink(path)
    return {"policy_contract_id": policy_id, "token_contract_id": token_id}


def set_policy_data(policy_id, policy_data, user_name):
    """Write the policy data dict into a policy agent contract."""
    state = get_state()
    data_path = _tmp_json(policy_data)
    try:
        with _op_lock:
            rego_policy_agent.set_policy_data(
                state, policy_id, user_name, data=data_path
            )
    finally:
        _safe_unlink(data_path)


def get_policy_data(policy_id, user_name):
    """Return the policy agent's current policy data as a dict."""
    state = get_state()
    with _op_lock:
        raw = rego_policy_agent.get_policy_data(state, policy_id, user_name)
    if isinstance(raw, str):
        return json.loads(raw) if raw else {}
    return raw or {}


def register_policy_trusted_issuer(
    policy_id, issuer_id, user_name, *, path, credential_types
):
    """Register a signature authority as a trusted issuer on a policy agent
    for one or more credential types at a given context path.
    """
    state = get_state()
    with _op_lock:
        rego_policy_agent.register_trusted_issuer(
            state,
            policy_id,
            issuer_id,
            user_name,
            path=path,
            credential_types=credential_types,
        )


def list_policy_trusted_issuers(policy_id, user_name):
    """Return the policy agent's registered trusted issuers as a dict."""
    state = get_state()
    with _op_lock:
        raw = rego_policy_agent.list_trusted_issuers(state, policy_id, user_name)
    if isinstance(raw, str):
        return json.loads(raw) if raw else {}
    return raw or {}


def list_token_trusted_issuers(token_id, user_name):
    """Return the rego token's registered trusted issuers as a dict.

    The single entry is the policy agent registered at expose-time; its
    key is the policy agent's contract id.
    """
    state = get_state()
    with _op_lock:
        raw = rego_token.list_trusted_issuers(state, token_id, user_name)
    if isinstance(raw, str):
        return json.loads(raw) if raw else {}
    return raw or {}


# ============================================================
# Asset use ops (consumer-side)
# ============================================================
def ensure_public_key_credential(wallet_id, token_id, user_name, keys_dir):
    """Ensure the wallet holds a publicKeyCredential if the asset's policy
    requires one.

    No-op if the policy doesn't require ``publicKeyCredential`` or the wallet
    already has one. Otherwise finds the policy's trusted external_key_authority
    for that credential type and binds a fresh session key to the wallet
    through it, which stores the issued credential directly in the wallet.

    Returns ``True`` if a credential was obtained, ``False`` if this was a
    no-op. Raises ``ValueError`` if the credential is required but no trusted
    issuer is registered for it.
    """
    state = get_state()
    with _op_lock:
        issuers_raw = rego_token.list_trusted_issuers(state, token_id, user_name)
        issuers = (
            json.loads(issuers_raw) if isinstance(issuers_raw, str) else (issuers_raw or {})
        )
        if not issuers:
            return False
        policy_id = next(iter(issuers.keys()))

        requirements = rego_policy_agent.get_requirements(state, policy_id, user_name)
        required_types = {t for types in requirements.values() for t in types}
        if PUBLIC_KEY_CREDENTIAL_TYPE not in required_types:
            return False

        vc_map_raw = signature_authority.get_vc_list(state, wallet_id, user_name)
        vc_map = json.loads(vc_map_raw) if isinstance(vc_map_raw, str) else (vc_map_raw or {})
        if PUBLIC_KEY_CREDENTIAL_TYPE in vc_map:
            return False

        policy_issuers_raw = rego_policy_agent.list_trusted_issuers(
            state, policy_id, user_name
        )
        policy_issuers = (
            json.loads(policy_issuers_raw)
            if isinstance(policy_issuers_raw, str)
            else (policy_issuers_raw or {})
        )
        eka_id = next(
            (
                contract_id
                for contract_id, entries in policy_issuers.items()
                for entry in (entries or [])
                if PUBLIC_KEY_CREDENTIAL_TYPE in (entry.get("credential_types") or [])
            ),
            None,
        )
        if eka_id is None:
            raise ValueError(
                "This asset's policy requires a publicKeyCredential, but no "
                "trusted issuer is registered for it."
            )

        external_key_authority.bind_external_key(
            state, eka_id, wallet_id, user_name, keys_dir=keys_dir
        )
        time.sleep(1)
        return True


def use_asset(*, wallet_id, token_id, guardian_url_port, user_name, output_dir=None):
    """Run the consumer download flow against a rego_policy_agent.

    1. Read the token's trusted-issuer list to discover the policy agent.
    2. Get the per-role credential requirements from the policy.
    3. Build a VP from the wallet covering the union of required types.
    4. Wrap it as the role-keyed presentation the rego_policy_agent expects.
    5. Issue a policy_decision credential from the policy.
    6. Download the (encrypted) data through the guardian.

    Returns ``(output_path, issued_vc_dict)``.
    """
    state = get_state()
    output_dir = output_dir or cfg.DOWNLOAD_OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)

    vp_path = _tmp_path(".json")
    presentation_path = _tmp_path(".json")
    issued_path = _tmp_path(".json")
    output_path = os.path.join(output_dir, f"download_{os.urandom(4).hex()}.bin")

    try:
        with _op_lock:
            issuers_raw = rego_token.list_trusted_issuers(state, token_id, user_name)
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

            # rego_policy_agent.get_requirements returns { role: [credential_type, ...] }
            requirements = rego_policy_agent.get_requirements(
                state, policy_id, user_name
            )
            time.sleep(1)
            # build one VP from the wallet covering every required credential type
            required_types = sorted(
                {t for types in requirements.values() for t in types}
            )
            signature_authority.get_vp(
                state,
                wallet_id,
                user_name,
                types=required_types,
                output_file=vp_path,
            )
            time.sleep(1)

            # the rego_policy_agent expects the presentation keyed by role:
            # { role: <verifiable presentation> }. Our policies use a single
            # "User" role, but key each required role to the VP for generality.
            with open(vp_path) as f:
                vp = json.load(f)
            presentation = {role: vp for role in requirements} or {"User": vp}
            with open(presentation_path, "w") as f:
                json.dump(presentation, f)

            rego_policy_agent.issue_policy_credential(
                state,
                policy_id,
                user_name,
                presentation=presentation_path,
                issued_credential=issued_path,
            )
            time.sleep(1)
            rego_token.do_operation(
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
        _safe_unlink(presentation_path)
        _safe_unlink(issued_path)
