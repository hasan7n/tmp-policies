import json
import logging

from django.http import Http404
from django.shortcuts import render

from .. import ledger_client, pdo_runner, registry_client
from ..did_utils import make_did, parse_did
from ..models import AppConfig
from ..url_safe_id import decode_cid, encode_cid
from ._helpers import (
    BaseView,
    JsonView,
    ValidationError,
    redirect_with_msg,
    require,
)

logger = logging.getLogger(__name__)


def _short_id(contract_id, n=12):
    """Display name for a wallet: short prefix of its contract_id."""
    return contract_id[:n]


def _user_wallet_ids(user_name):
    """List the user's *pure* wallet contract ids — signature_authority
    contracts they own that are NOT registered as assets.

    The signature_authority contract type is reused as the identity backing
    an asset, so the same family appears for both. The asset registry is the
    canonical place that says "this id is an asset," so we use it to subtract.
    """
    sa_ids = ledger_client.list_signature_authority_ids(user_name)
    if not sa_ids:
        return []
    try:
        asset_ids = {
            parse_did(a["did"])[0] for a in (registry_client.list_assets() or [])
        }
    except Exception:
        logger.exception("Failed to fetch assets while filtering wallets")
        asset_ids = set()
    return [cid for cid in sa_ids if cid not in asset_ids]


def _require_user_wallet(user_name, contract_id):
    """Raise 404 unless ``contract_id`` is one of this user's wallets."""
    if contract_id not in _user_wallet_ids(user_name):
        raise Http404(f"wallet not found: {contract_id}")


def _wallet_card(contract_id):
    return {
        "contract_id": contract_id,
        "cid_url": encode_cid(contract_id),
        "name": f"Wallet {_short_id(contract_id)}",
        "did": make_did(contract_id),
    }


# ============================================================
# Page views (server-rendered)
# ============================================================
class WalletsListView(BaseView):
    """GET: list wallets. POST: create a new wallet (single primary action)."""

    def get(self, request):
        user_name = AppConfig.get_instance().public_key
        wallets = [_wallet_card(cid) for cid in _user_wallet_ids(user_name)]
        return render(request, "wallets/list.html", {"wallets": wallets})

    def post(self, request):
        name = (request.POST.get("name") or "").strip()
        if not name:
            return redirect_with_msg("/wallets/", "Wallet name is required.", "error")

        user_name = AppConfig.get_instance().public_key
        try:
            pdo_runner.create_wallet(name, user_name)
        except Exception as e:
            logger.exception("Failed to create wallet")
            return redirect_with_msg(
                "/wallets/", f"Failed to create wallet: {e}", "error"
            )

        return redirect_with_msg("/wallets/", f'Wallet "{name}" created.', "success")


class WalletDetailView(BaseView):
    """GET-only: render the wallet dashboard. All mutating actions are JSON
    endpoints (see ``api.py``)."""

    def get(self, request, cid_url):
        contract_id = decode_cid(cid_url)
        user_name = AppConfig.get_instance().public_key
        _require_user_wallet(user_name, contract_id)
        wallet = _wallet_card(contract_id)

        signing_contexts, signing_contexts_error = [], None
        try:
            signing_contexts = pdo_runner.wallet_list_signing_contexts(
                contract_id, user_name
            )
        except Exception as e:
            logger.exception("Failed to list signing contexts")
            signing_contexts_error = str(e)

        vcs, vcs_error = {}, None
        try:
            vcs = pdo_runner.wallet_list_vcs(contract_id, user_name)
        except Exception as e:
            logger.exception("Failed to list wallet VCs")
            vcs_error = str(e)

        templates, templates_error = [], None
        try:
            templates = registry_client.list_credential_templates()
            for t in templates:
                t["claims_schema_json"] = json.dumps(t.get("claims_schema") or {})
        except Exception as e:
            logger.exception("Failed to fetch credential templates")
            templates_error = str(e)

        return render(
            request,
            "wallets/detail.html",
            {
                "wallet": wallet,
                "signing_contexts": signing_contexts,
                "signing_contexts_error": signing_contexts_error,
                "vcs": vcs,
                "vcs_error": vcs_error,
                "templates": templates,
                "templates_error": templates_error,
            },
        )


# ============================================================
# JSON endpoints (one logical action each)
# ============================================================
class WalletAddVCEndpoint(JsonView):
    """POST {vc: {...}} — store a VC in the wallet."""

    def handle(self, request, data, cid_url):
        contract_id = decode_cid(cid_url)
        user_name = AppConfig.get_instance().public_key
        _require_user_wallet(user_name, contract_id)
        vc = require(data, "vc")
        if not isinstance(vc, dict):
            raise ValidationError("'vc' must be a JSON object")

        pdo_runner.wallet_add_vc(contract_id, vc, user_name)
        return {"ok": True, "message": "Credential added."}


class WalletRegisterIssuerEndpoint(JsonView):
    """POST {name, description?, extensible?} — register a signing context."""

    def handle(self, request, data, cid_url):
        contract_id = decode_cid(cid_url)
        user_name = AppConfig.get_instance().public_key
        _require_user_wallet(user_name, contract_id)
        name = require(data, "name")
        description = (data.get("description") or "").strip() or f"issuer {name}"
        extensible = bool(data.get("extensible", False))

        pdo_runner.register_signing_context(
            contract_id,
            user_name,
            path=[name],
            description=description,
            extensible=extensible,
        )

        return {
            "ok": True,
            "message": f'Issuer "{name}" registered.',
            "issuer": {
                "did": make_did(contract_id, name),
                "path": [name],
                "description": description,
                "extensible": extensible,
            },
        }


class WalletSignCredentialEndpoint(JsonView):
    """POST {signing_context, template_type, subject_did, claims} — sign a VC.

    Returns the signed VC JSON on success.
    """

    def handle(self, request, data, cid_url):
        contract_id = decode_cid(cid_url)
        user_name = AppConfig.get_instance().public_key
        _require_user_wallet(user_name, contract_id)
        signing_context, template_type, subject_did = require(
            data, "signing_context", "template_type", "subject_did"
        )
        claims = data.get("claims") or {}
        if not isinstance(claims, dict):
            raise ValidationError("'claims' must be a JSON object")

        subject_contract_id, _ = parse_did(subject_did)
        credential = {
            "type": [template_type],
            "issuer": {"id": make_did(contract_id, signing_context)},
            "credentialSubject": {
                "subject": {
                    "id": make_did(subject_contract_id),
                },
                "claims": claims,
            },
        }

        signed_vc = pdo_runner.sign_credential(
            contract_id,
            signing_context_path=[signing_context],
            credential_dict=credential,
            user_name=user_name,
        )
        return {"ok": True, "signed_vc": signed_vc}
