import json
import logging

from django.conf import settings
from django.http import Http404
from django.shortcuts import redirect, render

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


def _guardian_url_port(host, port):
    """Compose the canonical guardian URL the download token contract stores."""
    return f"http://{host}:{port}"


def _resolve_policy_id(token_contract_id, user_name):
    """Return the policy agent contract id for a given token, by reading the
    token's trusted-issuer list. The token registers exactly one issuer at
    expose-time: the policy agent. Returns ``None`` if none is registered.
    """
    issuers = pdo_runner.list_token_trusted_issuers(token_contract_id, user_name)
    if not issuers:
        return None
    return next(iter(issuers.keys()))


def _flatten_policy_issuers(raw_issuers):
    """Flatten the policy agent's trusted-issuer map into display rows.

    ``raw_issuers`` is shaped as ``{contract_id: [entry, ...]}`` where each
    entry has ``verifying_context.prefix_path`` and ``credential_types``.
    Returns a list of ``{"did", "credential_types"}`` dicts, one per
    (contract_id, prefix_path) pair.
    """
    rows = []
    for contract_id, entries in (raw_issuers or {}).items():
        for entry in entries or []:
            prefix_path = (
                (entry.get("verifying_context") or {}).get("prefix_path") or []
            )
            rows.append(
                {
                    "did": make_did(contract_id, prefix_path),
                    "credential_types": entry.get("credential_types") or [],
                }
            )
    return rows


def _short_id(contract_id, n=12):
    return contract_id[:n]


def _user_wallet_cards(user_name):
    """Wallet picker entries for the asset list / asset dashboard 'Use' modal.

    Mirrors ``views.wallets._user_wallet_ids`` but inlined to avoid a circular
    import. Pure wallets = signature_authority contracts not registered as
    assets.
    """
    sa_ids = ledger_client.list_signature_authority_ids(user_name)
    if not sa_ids:
        return []
    try:
        asset_ids = {
            parse_did(a["did"])[0] for a in (registry_client.list_assets() or [])
        }
    except Exception:
        logger.exception("Failed to fetch assets while building wallet picker")
        asset_ids = set()
    return [
        {"contract_id": cid, "name": f"Wallet {_short_id(cid)}"}
        for cid in sa_ids
        if cid not in asset_ids
    ]


def _require_user_asset(user_name, contract_id):
    """Raise 404 unless ``contract_id`` is one of this user's assets.

    Asset ownership = (a) the contract id is in the user's on-ledger
    contract list, and (b) the DID is registered in the asset registry.
    """
    if not ledger_client.user_owns_contract(user_name, contract_id):
        raise Http404(f"asset not found: {contract_id}")
    try:
        registry_client.get_asset_by_did(make_did(contract_id))
    except Exception:
        raise Http404(f"asset not registered: {contract_id}")


class AssetsListView(BaseView):
    """GET-only: list all assets in the registry, annotated with ownership."""

    def get(self, request):
        user_name = AppConfig.get_instance().public_key
        assets = []
        list_error = None
        try:
            assets = registry_client.list_assets() or []
            owned_ids = set(ledger_client.list_signature_authority_ids(user_name))
            for a in assets:
                cid, _ = parse_did(a["did"])
                a["contract_id"] = cid
                a["cid_url"] = encode_cid(cid)
                a["is_local"] = cid in owned_ids
        except Exception as e:
            logger.exception("Failed to fetch assets")
            list_error = str(e)

        wallets = _user_wallet_cards(user_name)
        return render(
            request,
            "assets/list.html",
            {
                "assets": assets,
                "wallets": wallets,
                "list_error": list_error,
            },
        )


class AssetSetupView(BaseView):
    """GET: registration form. POST: register an asset.

    The asset still gets its own (signature_authority-backed) contract so
    it has a stable DID in the registry. Policy/token contracts are only
    created later in the expose flow.
    """

    def get(self, request):
        return render(request, "assets/setup.html")

    def post(self, request):
        name = (request.POST.get("name") or "").strip()
        data_source = (request.POST.get("data_source") or "").strip()
        guardian_url = (request.POST.get("guardian_url") or "").strip()
        guardian_port = (request.POST.get("guardian_port") or "").strip()

        if not all([name, data_source, guardian_url, guardian_port]):
            return render(
                request,
                "assets/setup.html",
                {
                    "form": request.POST,
                    "error": "All fields are required.",
                },
            )

        config = AppConfig.get_instance()
        user_name = config.public_key

        try:
            contract_id = pdo_runner.create_wallet(name, user_name)
            did = make_did(contract_id)

            registry_asset = registry_client.register_asset(
                name=name,
                did=did,
                metadata={
                    "guardian_url": guardian_url,
                    "guardian_port": guardian_port,
                    "data_source": data_source,
                },
            )

            registry_pk = registry_asset["id"]
            asset_registry_url = (
                f"{settings.ASSET_REGISTRY_URL.rstrip('/')}/api/assets/{registry_pk}/"
            )
            registry_client.update_asset_metadata(
                registry_pk, {"asset_registry_url": asset_registry_url}
            )

        except Exception as e:
            logger.exception("Failed to register asset")
            return render(
                request,
                "assets/setup.html",
                {
                    "form": request.POST,
                    "error": f"Failed to register asset: {e}",
                },
            )

        return redirect_with_msg("/", f'Asset "{name}" registered.', "success")


class AssetDashboardView(BaseView):
    """GET-only: render the per-asset dashboard.

    Determines whether the asset already has a policy agent by reading the
    registry's ``policy_contract`` metadata (a token DID, set at expose time)
    and querying the token's trusted-issuer list. When a policy exists, the
    dashboard also lists its currently registered trusted issuers; otherwise
    it surfaces the Expose form.
    """

    def get(self, request, cid_url):
        contract_id = decode_cid(cid_url)
        user_name = AppConfig.get_instance().public_key
        _require_user_asset(user_name, contract_id)
        did = make_did(contract_id)

        try:
            asset = registry_client.get_asset_by_did(did) or {}
        except Exception as e:
            logger.exception("Failed to fetch asset from registry")
            asset = {}
            registry_error = str(e)
        else:
            registry_error = None

        metadata = asset.get("metadata", {}) or {}
        ctx = {
            "asset": {
                "contract_id": contract_id,
                "cid_url": cid_url,
                "did": did,
                "name": asset.get("name") or f"Asset {_short_id(contract_id)}",
            },
            "wallets": _user_wallet_cards(user_name),
            "has_policy": False,
            "policy_contract_id": None,
            "token_contract_id": None,
            "policy_issuers": [],
            "policy_issuers_error": None,
            "policy_data": {},
            "policy_data_json": "",
            "policy_data_error": None,
            "registry_error": registry_error,
            "templates": [],
            "templates_error": None,
            "policy_details": {},
            "credential_templates": [],
            "credential_templates_error": None,
        }

        token_did = metadata.get("policy_contract", "")
        if token_did:
            try:
                token_id, _ = parse_did(token_did)
                policy_id = _resolve_policy_id(token_id, user_name)
            except Exception as e:
                logger.exception("Failed to resolve policy id from token")
                ctx["policy_issuers_error"] = str(e)
                policy_id = None
                token_id = None

            if policy_id:
                ctx["has_policy"] = True
                ctx["policy_contract_id"] = policy_id
                ctx["token_contract_id"] = token_id
                try:
                    raw_issuers = pdo_runner.list_policy_trusted_issuers(
                        policy_id, user_name
                    )
                    ctx["policy_issuers"] = _flatten_policy_issuers(raw_issuers)
                except Exception as e:
                    logger.exception("Failed to list policy trusted issuers")
                    ctx["policy_issuers_error"] = str(e)
                try:
                    ctx["policy_data"] = pdo_runner.get_policy_data(
                        policy_id, user_name
                    )
                    ctx["policy_data_json"] = json.dumps(ctx["policy_data"], indent=2)
                except Exception as e:
                    logger.exception("Failed to get policy data")
                    ctx["policy_data_error"] = str(e)
                    ctx["policy_data_json"] = ""
                try:
                    ctx["credential_templates"] = (
                        registry_client.list_credential_templates()
                    )
                except Exception as e:
                    logger.exception("Failed to fetch credential templates")
                    ctx["credential_templates_error"] = str(e)

        if not ctx["has_policy"]:
            try:
                # only Rego-backed templates can be provisioned as subpolicies
                ctx["templates"] = [
                    t
                    for t in registry_client.list_policy_templates()
                    if (t.get("rego_source") or "").strip()
                ]
                for t in ctx["templates"]:
                    t["policy_data_schema_json"] = json.dumps(
                        t.get("policy_data_schema") or {}
                    )
                # rego source + README per policy, for the "View" popup (keyed by id)
                ctx["policy_details"] = {
                    str(t["id"]): {
                        "name": t.get("name", ""),
                        "rego_source": t.get("rego_source", ""),
                        "readme": t.get("readme", ""),
                    }
                    for t in ctx["templates"]
                }
            except Exception as e:
                logger.exception("Failed to fetch policy templates")
                ctx["templates_error"] = str(e)

        return render(request, "assets/dashboard.html", ctx)


class AssetExposeView(BaseView):
    """POST-only now: create policy + token contracts, set policy data, and
    update the registry. The form lives inside the dashboard page; on success
    we redirect back there.
    """

    def get(self, request, cid_url):
        return redirect("asset_dashboard", cid_url=cid_url)

    def post(self, request, cid_url):
        contract_id = decode_cid(cid_url)
        user_name = AppConfig.get_instance().public_key
        _require_user_asset(user_name, contract_id)
        did = make_did(contract_id)
        dashboard_url = f"/assets/{cid_url}/"

        policy_data_raw = (request.POST.get("policy_data") or "").strip()
        try:
            policy_data = json.loads(policy_data_raw) if policy_data_raw else {}
        except json.JSONDecodeError as e:
            return redirect_with_msg(
                dashboard_url, f"Invalid policy data JSON: {e}", "error"
            )

        # The owner may select one or more policy templates; each becomes a Rego
        # subpolicy provisioned into the rego_policy_agent via set_rego_policy.
        policy_template_ids = request.POST.getlist("policy_templates")
        if not policy_template_ids:
            return redirect_with_msg(
                dashboard_url, "Select at least one policy.", "error"
            )

        try:
            rego_modules = []
            for tid in policy_template_ids:
                tpl = registry_client.get_policy_template(tid)
                source = (tpl.get("rego_source") or "").strip()
                if not source:
                    return redirect_with_msg(
                        dashboard_url,
                        f"Policy '{tpl.get('name', tid)}' has no rego source.",
                        "error",
                    )
                rego_modules.append([tpl["name"], source])
        except Exception as e:
            logger.exception("Failed to load selected policy templates")
            return redirect_with_msg(
                dashboard_url, f"Failed to load selected policies: {e}", "error"
            )

        # Guardian info is on the registry record (set at asset registration).
        try:
            meta = (registry_client.get_asset_by_did(did) or {}).get(
                "metadata", {}
            ) or {}
        except Exception as e:
            return redirect_with_msg(
                dashboard_url, f"Failed to read asset metadata: {e}", "error"
            )
        guardian_host = meta.get("guardian_url", "")
        guardian_port = meta.get("guardian_port", "")
        if not guardian_host or not guardian_port:
            return redirect_with_msg(
                dashboard_url, "Guardian URL/port missing on this asset.", "error"
            )

        guardian = _guardian_url_port(guardian_host, guardian_port)
        asset_name = meta.get("name") or _short_id(contract_id)

        try:
            result = pdo_runner.create_asset_policy(
                f"Policy for {asset_name}", guardian, user_name, rego_modules
            )

            if policy_data:
                pdo_runner.set_policy_data(
                    result["policy_contract_id"], policy_data, user_name
                )

            token_did = make_did(result["token_contract_id"])
            registry_client.update_asset_metadata_by_did(
                did,
                {"policy_contract": token_did, "policy_data": policy_data},
            )

        except Exception as e:
            logger.exception("Failed to expose asset")
            return redirect_with_msg(
                dashboard_url, f"Failed to expose asset: {e}", "error"
            )

        return redirect_with_msg(
            dashboard_url, "Asset exposed via download policy.", "success"
        )


# ============================================================
# JSON endpoints
# ============================================================
class AssetUseEndpoint(JsonView):
    """POST {asset_did, wallet_id} — run the consumer download flow and
    return ``{output_file, issued_vc}``."""

    def handle(self, request, data, **kwargs):
        asset_did = require(data, "asset_did")
        wallet_id = require(data, "wallet_id")

        user_name = AppConfig.get_instance().public_key
        if not ledger_client.user_owns_contract(user_name, wallet_id):
            raise ValidationError(f"wallet not found: {wallet_id}")

        asset_info = registry_client.get_asset_by_did(asset_did)
        metadata = asset_info.get("metadata", {}) or {}

        token_did = metadata.get("policy_contract", "")
        if not token_did:
            raise ValidationError(
                "Asset has not been exposed (no policy_contract in registry)."
            )

        token_contract_id, _ = parse_did(token_did)
        guardian = _guardian_url_port(
            metadata.get("guardian_url", ""),
            metadata.get("guardian_port", ""),
        )

        output_path, issued_vc = pdo_runner.use_asset(
            wallet_id=wallet_id,
            token_id=token_contract_id,
            guardian_url_port=guardian,
            user_name=user_name,
        )
        return {"ok": True, "output_file": output_path, "issued_vc": issued_vc}


class AssetRegisterPolicyIssuerEndpoint(JsonView):
    """POST {issuer_did, credential_types: [...]} — register a signature
    authority (identified by its DID, optionally with a ``#path`` signing
    context) as a trusted issuer for one or more credential types on the
    asset's policy agent.
    """

    def handle(self, request, data, cid_url):
        contract_id = decode_cid(cid_url)
        user_name = AppConfig.get_instance().public_key
        _require_user_asset(user_name, contract_id)
        did = make_did(contract_id)

        issuer_did = require(data, "issuer_did")
        credential_types = data.get("credential_types")
        if not isinstance(credential_types, list) or not credential_types:
            raise ValidationError(
                "'credential_types' must be a non-empty list of strings"
            )

        try:
            issuer_contract_id, issuer_path = parse_did(issuer_did)
        except ValueError as e:
            raise ValidationError(str(e))
        path = [issuer_path] if issuer_path else []

        try:
            asset = registry_client.get_asset_by_did(did) or {}
        except Exception as e:
            raise ValidationError(f"failed to look up asset in registry: {e}")
        token_did = (asset.get("metadata", {}) or {}).get("policy_contract", "")
        if not token_did:
            raise ValidationError("Asset has no policy agent yet (expose it first).")

        token_id, _ = parse_did(token_did)
        policy_id = _resolve_policy_id(token_id, user_name)
        if not policy_id:
            raise ValidationError("Token contract has no registered policy agent.")

        pdo_runner.register_policy_trusted_issuer(
            policy_id,
            issuer_contract_id,
            user_name,
            path=path,
            credential_types=credential_types,
        )
        return {
            "ok": True,
            "message": "Issuer registered for: " + ", ".join(credential_types),
        }


class AssetUpdatePolicyDataEndpoint(JsonView):
    """POST {policy_data: {...}} — call set_policy_data on the asset's policy
    agent. Also mirrors the new data into the asset registry metadata so the
    list view's policy_data field stays in sync.
    """

    def handle(self, request, data, cid_url):
        contract_id = decode_cid(cid_url)
        user_name = AppConfig.get_instance().public_key
        _require_user_asset(user_name, contract_id)
        did = make_did(contract_id)

        policy_data = data.get("policy_data")
        if not isinstance(policy_data, dict):
            raise ValidationError("'policy_data' must be a JSON object")

        try:
            asset = registry_client.get_asset_by_did(did) or {}
        except Exception as e:
            raise ValidationError(f"failed to look up asset in registry: {e}")
        token_did = (asset.get("metadata", {}) or {}).get("policy_contract", "")
        if not token_did:
            raise ValidationError("Asset has no policy agent yet (expose it first).")

        token_id, _ = parse_did(token_did)
        policy_id = _resolve_policy_id(token_id, user_name)
        if not policy_id:
            raise ValidationError("Token contract has no registered policy agent.")

        pdo_runner.set_policy_data(policy_id, policy_data, user_name)

        try:
            registry_client.update_asset_metadata_by_did(
                did, {"policy_data": policy_data}
            )
        except Exception:
            logger.exception("Failed to mirror policy_data into registry metadata")

        return {"ok": True, "message": "Policy data updated."}
