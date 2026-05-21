"""Ledger client: read the user's contracts directly from CCF.

Replaces the local ``app_entity`` table. The CCF transaction processor now
maintains a reverse index ``verifying_key -> [{contract_id, contract_family}]``
populated piggybacked on ``register_contract``. We call its read endpoint
``get_user_contracts`` to materialize the list on demand.

The ``contract_family`` value on the ledger is the *contract class name* used
at registration time, e.g. ``"signature_authority"``, ``"policy_agent"``,
``"download_token"`` — that's what ``pcontract.register_contract`` passes
through. Filtering on it is how we tell wallets from policy/token contracts.
"""

import logging
import threading

# pdo_config sets env vars; must import before any pdo.* import.
from . import pdo_config as cfg  # noqa: F401

from pdo.common.keys import ServiceKeys
from pdo.submitter.create import create_submitter

from .pdo_state import get_state

logger = logging.getLogger(__name__)
_op_lock = threading.Lock()

# Contract-class strings as registered on the ledger (see
# pdo-contracts/private-data-objects/client/pdo/client/commands/contract.py:269,
# which passes ``contract_class`` as the family).
FAMILY_SIGNATURE_AUTHORITY = "signature_authority"
FAMILY_POLICY_AGENT = "policy_agent"
FAMILY_DOWNLOAD_TOKEN = "download_token"


def _load_user_keys(user_name):
    """Load the user's keypair as a ``ServiceKeys`` instance.

    Resolved through the same ``[Key].SearchPath`` PDO uses when registering
    contracts, so this keeps the "wallet for X" the same identity as the
    creator recorded on the ledger.
    """
    state = get_state()
    keypath = state.get(["Key", "SearchPath"])
    keyfile = f"{user_name}_private.pem"
    return ServiceKeys.read_from_file(keyfile, keypath)


def get_user_contracts(user_name):
    """Return the user's on-ledger contract list.

    Output: ``[{"contract_id": str, "contract_family": str}, ...]``.
    """
    state = get_state()
    ledger_config = state.get(["Ledger"])
    user_keys = _load_user_keys(user_name)

    with _op_lock:
        submitter = create_submitter(ledger_config, pdo_signer=user_keys)
        response = submitter.get_user_contracts(user_keys)

    entries = response.get("entries", []) if isinstance(response, dict) else []
    # Defensive normalization — the on-ledger struct guarantees these fields,
    # but tolerate trailing future fields.
    return [
        {
            "contract_id": e["contract_id"],
            "contract_family": e["contract_family"],
        }
        for e in entries
        if isinstance(e, dict) and "contract_id" in e and "contract_family" in e
    ]


def list_signature_authority_ids(user_name):
    """Contract IDs owned by ``user_name`` whose family is signature_authority.

    These are the candidates for "wallets" and "asset identity contracts".
    Whether a given id is a pure wallet vs the identity contract behind an
    asset is decided by the asset registry (does this DID appear there?).
    """
    return [
        e["contract_id"]
        for e in get_user_contracts(user_name)
        if e["contract_family"] == FAMILY_SIGNATURE_AUTHORITY
    ]


def user_owns_contract(user_name, contract_id):
    """True iff ``contract_id`` appears in the user's on-ledger contract list."""
    return any(e["contract_id"] == contract_id for e in get_user_contracts(user_name))
