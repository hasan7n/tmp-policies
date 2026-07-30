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

ISSUER_TYPES = ("manual", "external_key_authority")


def _short_id(contract_id, n=12):
    """Display name for an issuer: short prefix of its contract_id."""
    return contract_id[:n]


def _user_manual_issuer_ids(user_name):
    """List the user's "manual" issuer contract ids — signature_authority
    contracts they own that are NOT registered as assets.

    The signature_authority contract type is also reused as the identity
    backing an asset, so the same family appears for both. The asset registry
    is the canonical place that says "this id is an asset," so we use it to
    subtract.
    """
    sa_ids = ledger_client.list_signature_authority_ids(user_name)
    if not sa_ids:
        return []
    try:
        asset_ids = {
            parse_did(a["did"])[0] for a in (registry_client.list_assets() or [])
        }
    except Exception:
        logger.exception("Failed to fetch assets while filtering issuers")
        asset_ids = set()
    return [cid for cid in sa_ids if cid not in asset_ids]


def _issuer_card(contract_id, kind):
    return {
        "contract_id": contract_id,
        "cid_url": encode_cid(contract_id),
        "name": f"Issuer {_short_id(contract_id)}",
        "did": make_did(contract_id),
        "kind": kind,
        "kind_label": (
            "External Key Authority" if kind == "external_key_authority" else "Manual"
        ),
    }


def _issuer_cards(user_name):
    cards = [_issuer_card(cid, "manual") for cid in _user_manual_issuer_ids(user_name)]
    cards += [
        _issuer_card(cid, "external_key_authority")
        for cid in ledger_client.list_external_key_authority_ids(user_name)
    ]
    return cards


def _issuer_kind(user_name, contract_id):
    """Return this issuer's kind ("manual" / "external_key_authority"), or
    None if ``contract_id`` isn't one of this user's issuers."""
    if contract_id in ledger_client.list_external_key_authority_ids(user_name):
        return "external_key_authority"
    if contract_id in _user_manual_issuer_ids(user_name):
        return "manual"
    return None


def _require_user_issuer(user_name, contract_id):
    """Raise 404 unless ``contract_id`` is one of this user's issuers.
    Returns the issuer's kind."""
    kind = _issuer_kind(user_name, contract_id)
    if kind is None:
        raise Http404(f"issuer not found: {contract_id}")
    return kind


# ============================================================
# Page views (server-rendered)
# ============================================================
class IssuersListView(BaseView):
    """GET: list issuers. POST: create a new issuer (single primary action)."""

    def get(self, request):
        user_name = AppConfig.get_instance().public_key
        issuers = _issuer_cards(user_name)
        return render(request, "issuers/list.html", {"issuers": issuers})

    def post(self, request):
        name = (request.POST.get("name") or "").strip()
        issuer_type = (request.POST.get("issuer_type") or "").strip()
        if not name:
            return redirect_with_msg("/issuers/", "Issuer name is required.", "error")
        if issuer_type not in ISSUER_TYPES:
            return redirect_with_msg("/issuers/", "Select an issuer type.", "error")

        user_name = AppConfig.get_instance().public_key
        try:
            if issuer_type == "manual":
                pdo_runner.create_manual_issuer(name, user_name)
            else:
                pdo_runner.create_external_key_authority_issuer(name, user_name)
        except Exception as e:
            logger.exception("Failed to create issuer")
            return redirect_with_msg(
                "/issuers/", f"Failed to create issuer: {e}", "error"
            )

        return redirect_with_msg("/issuers/", f'Issuer "{name}" created.', "success")


class IssuerDetailView(BaseView):
    """GET-only: render the issuer dashboard. All mutating actions are JSON
    endpoints below."""

    def get(self, request, cid_url):
        contract_id = decode_cid(cid_url)
        user_name = AppConfig.get_instance().public_key
        kind = _require_user_issuer(user_name, contract_id)
        issuer = _issuer_card(contract_id, kind)

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
            logger.exception("Failed to list issuer VCs")
            vcs_error = str(e)

        # Only manual issuers can sign arbitrary credentials from a signing
        # context; an external_key_authority's sign_credential does something
        # else entirely (binds a session key to a wallet).
        templates, templates_error = [], None
        if kind == "manual":
            try:
                templates = registry_client.list_credential_templates()
                for t in templates:
                    t["claims_schema_json"] = json.dumps(t.get("claims_schema") or {})
            except Exception as e:
                logger.exception("Failed to fetch credential templates")
                templates_error = str(e)

        return render(
            request,
            "issuers/detail.html",
            {
                "issuer": issuer,
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
class IssuerAddVCEndpoint(JsonView):
    """POST {vc: {...}} — store a VC in the issuer's credential store."""

    def handle(self, request, data, cid_url):
        contract_id = decode_cid(cid_url)
        user_name = AppConfig.get_instance().public_key
        _require_user_issuer(user_name, contract_id)
        vc = require(data, "vc")
        if not isinstance(vc, dict):
            raise ValidationError("'vc' must be a JSON object")

        pdo_runner.wallet_add_vc(contract_id, vc, user_name)
        return {"ok": True, "message": "Credential added."}


class IssuerRegisterSigningContextEndpoint(JsonView):
    """POST {name, description?, extensible?} — register a signing context."""

    def handle(self, request, data, cid_url):
        contract_id = decode_cid(cid_url)
        user_name = AppConfig.get_instance().public_key
        _require_user_issuer(user_name, contract_id)
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
            "message": f'Signing context "{name}" registered.',
            "issuer": {
                "did": make_did(contract_id, name),
                "path": [name],
                "description": description,
                "extensible": extensible,
            },
        }


class IssuerSignCredentialEndpoint(JsonView):
    """POST {signing_context, template_type, subject_did, claims} — sign a VC and
    store it directly in the subject's wallet. Manual issuers only: an
    external_key_authority's sign_credential is a different operation
    (binding a session key to a wallet), not arbitrary VC issuance.
    """

    def handle(self, request, data, cid_url):
        contract_id = decode_cid(cid_url)
        user_name = AppConfig.get_instance().public_key
        kind = _require_user_issuer(user_name, contract_id)
        if kind != "manual":
            raise ValidationError("Only manual issuers can sign credentials.")

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
        # Store the signed credential straight into the subject's wallet.
        pdo_runner.wallet_add_vc(subject_contract_id, signed_vc, user_name)
        return {
            "ok": True,
            "message": f"Credential issued and stored in {subject_did}.",
        }
