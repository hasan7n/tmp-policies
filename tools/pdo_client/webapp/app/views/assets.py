import json
import logging

from django.conf import settings
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render

from .. import (
    channel_keys,
    guardian_launcher,
    ledger_client,
    pdo_runner,
    registry_client,
)
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
from ._streaming import SkipStep, stream_steps

logger = logging.getLogger(__name__)


def _json_body(request):
    """Parse a JSON request body into a dict (empty dict if absent/invalid)."""
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


def _guardian_url_port(host, port):
    """Compose the canonical guardian URL the rego token contract stores."""
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
            prefix_path = (entry.get("verifying_context") or {}).get(
                "prefix_path"
            ) or []
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
                # An asset can only be "used" once it is behind a guardian.
                a["has_guardian"] = bool((a.get("metadata") or {}).get("guardian_url"))
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
    """GET: registration form. POST: deploy a guardian for the data and register
    the asset.

    Registering an asset also starts a guardian serving the given data path; we
    wait for the guardian to be healthy before recording it on the asset, so the
    asset is only created once it is actually behind a running guardian.
    """

    def get(self, request):
        return render(request, "assets/setup.html")

    def _error(self, request, message):
        return render(
            request,
            "assets/setup.html",
            {"form": request.POST, "error": message},
        )

    def post(self, request):
        name = (request.POST.get("name") or "").strip()
        data_source = (request.POST.get("data_source") or "").strip()

        if not all([name, data_source]):
            return self._error(request, "All fields are required.")

        config = AppConfig.get_instance()
        user_name = config.public_key

        # Deploy the guardian first and wait until it is up; only then register
        # the asset, so an asset never exists without a working guardian.
        try:
            guardian_url, guardian_port = guardian_launcher.deploy_guardian(
                data_source
            )
            guardian_launcher.wait_until_healthy(guardian_url, guardian_port)
        except Exception as e:
            logger.exception("Failed to deploy guardian")
            return self._error(request, f"Failed to deploy guardian: {e}")

        try:
            contract_id = pdo_runner.create_wallet(name, user_name)
            did = make_did(contract_id)

            registry_asset = registry_client.register_asset(
                name=name,
                did=did,
                metadata={
                    "data_source": data_source,
                    "guardian_url": guardian_url,
                    "guardian_port": guardian_port,
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
            return self._error(request, f"Failed to register asset: {e}")

        return redirect_with_msg(
            "/", f'Asset "{name}" registered and running behind a guardian.', "success"
        )


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
        guardian_url = metadata.get("guardian_url", "")
        guardian_port = metadata.get("guardian_port", "")
        guardian_deployed = bool(guardian_url and guardian_port)
        ctx = {
            "asset": {
                "contract_id": contract_id,
                "cid_url": cid_url,
                "did": did,
                "name": asset.get("name") or f"Asset {_short_id(contract_id)}",
            },
            "wallets": _user_wallet_cards(user_name),
            "guardian_deployed": guardian_deployed,
            "guardian_url": guardian_url,
            "guardian_port": guardian_port,
            "guardian_endpoint": (
                _guardian_url_port(guardian_url, guardian_port)
                if guardian_deployed
                else ""
            ),
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
            "credential_type_options": [],
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

            # Credential types the expose form's inline "trusted issuers" section
            # offers as checkboxes.
            try:
                ctx["credential_templates"] = (
                    registry_client.list_credential_templates()
                )
                ctx["credential_type_options"] = [
                    t.get("template_type") for t in ctx["credential_templates"]
                ]
            except Exception as e:
                logger.exception("Failed to fetch credential templates")
                ctx["credential_templates_error"] = str(e)

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

        # Trusted issuers added inline in the expose form (optional). The JS
        # serializes each box as {"did", "credential_types": [...]} into a hidden
        # field; they are registered on the new policy after it is created.
        trusted_issuers_raw = (request.POST.get("trusted_issuers") or "").strip()
        try:
            trusted_issuers = json.loads(trusted_issuers_raw) if trusted_issuers_raw else []
        except json.JSONDecodeError:
            trusted_issuers = []
        if not isinstance(trusted_issuers, list):
            trusted_issuers = []

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

        # The asset is now exposed; register any trusted issuers from the form as
        # a best effort. A failed issuer is reported but doesn't undo the expose —
        # it can be added later from the dashboard's Trusted Issuers section.
        policy_id = result["policy_contract_id"]
        issuer_errors = []
        for entry in trusted_issuers:
            if not isinstance(entry, dict):
                continue
            entry_did = (entry.get("did") or "").strip()
            credential_types = entry.get("credential_types") or []
            if not entry_did or not credential_types:
                continue
            try:
                issuer_contract_id, issuer_path = parse_did(entry_did)
                pdo_runner.register_policy_trusted_issuer(
                    policy_id,
                    issuer_contract_id,
                    user_name,
                    path=[issuer_path] if issuer_path else [],
                    credential_types=credential_types,
                )
            except Exception as e:
                logger.exception("Failed to register trusted issuer %s", entry_did)
                issuer_errors.append(f"{entry_did}: {e}")

        if issuer_errors:
            return redirect_with_msg(
                dashboard_url,
                "Asset exposed, but some trusted issuers failed: "
                + "; ".join(issuer_errors),
                "error",
            )

        return redirect_with_msg(
            dashboard_url, "Asset exposed via rego policy.", "success"
        )


# ============================================================
# JSON endpoints
# ============================================================
class AssetUseEndpoint(JsonView):
    """POST {asset_did, wallet_id} — run the consumer download flow, decrypt the
    downloaded data with the user's private channel key, and return ``{data}``.
    """

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

        output_path, _ = pdo_runner.use_asset(
            wallet_id=wallet_id,
            token_id=token_contract_id,
            guardian_url_port=guardian,
            user_name=user_name,
        )
        decrypted = channel_keys.decrypt_download(user_name, output_path)
        return {"ok": True, "data": decrypted}


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


# ============================================================
# Streaming variants (live per-step progress)
#
# Same work as the register / expose / use handlers above, but emitted as a
# stream of progress steps (see app/views/_streaming.py) so the UI can show what
# is happening behind the scenes. The page-form / JSON handlers above remain as
# the plain fallbacks.
# ============================================================
class AssetSetupStreamView(BaseView):
    """POST {name, data_source} — deploy a guardian then register the asset,
    streaming progress. JS variant of :class:`AssetSetupView`."""

    http_method_names = ["post"]

    def post(self, request):
        data = _json_body(request)
        name = (data.get("name") or "").strip()
        data_source = (data.get("data_source") or "").strip()
        if not name or not data_source:
            return JsonResponse(
                {"error": "name and data_source are required"}, status=400
            )
        user_name = AppConfig.get_instance().public_key

        def deploy(ctx):
            url, port = guardian_launcher.deploy_guardian(data_source)
            ctx["guardian_url"], ctx["guardian_port"] = url, port
            return {"detail": f"{url}:{port}"}

        def wait(ctx):
            guardian_launcher.wait_until_healthy(
                ctx["guardian_url"], ctx["guardian_port"]
            )

        def contract(ctx):
            ctx["contract_id"] = pdo_runner.create_wallet(name, user_name)
            return {"detail": _short_id(ctx["contract_id"])}

        def register(ctx):
            did = make_did(ctx["contract_id"])
            reg = registry_client.register_asset(
                name=name,
                did=did,
                metadata={
                    "data_source": data_source,
                    "guardian_url": ctx["guardian_url"],
                    "guardian_port": ctx["guardian_port"],
                },
            )
            pk = reg["id"]
            registry_client.update_asset_metadata(
                pk,
                {
                    "asset_registry_url": (
                        f"{settings.ASSET_REGISTRY_URL.rstrip('/')}/api/assets/{pk}/"
                    )
                },
            )

        steps = [
            ("guardian", "Deploying the guardian", deploy),
            ("health", "Waiting for the guardian to be healthy", wait),
            ("contract", "Creating the asset contract", contract),
            ("register", "Registering the asset", register),
        ]
        return stream_steps(
            steps,
            complete=lambda ctx: {
                "redirect": "/",
                "message": f'Asset "{name}" registered and running behind a guardian.',
            },
        )


class AssetExposeStreamView(BaseView):
    """POST {policy_templates: [...], policy_data, trusted_issuers: [...]} —
    create the policy + token, set data, update the registry, and register
    trusted issuers, streaming progress. JS variant of :class:`AssetExposeView`."""

    http_method_names = ["post"]

    def post(self, request, cid_url):
        contract_id = decode_cid(cid_url)
        user_name = AppConfig.get_instance().public_key
        _require_user_asset(user_name, contract_id)
        did = make_did(contract_id)
        dashboard_url = f"/assets/{cid_url}/"

        data = _json_body(request)
        policy_template_ids = data.get("policy_templates") or []
        if not isinstance(policy_template_ids, list) or not policy_template_ids:
            return JsonResponse({"error": "Select at least one policy."}, status=400)

        policy_data_raw = (data.get("policy_data") or "").strip()
        try:
            policy_data = json.loads(policy_data_raw) if policy_data_raw else {}
        except json.JSONDecodeError as e:
            return JsonResponse({"error": f"Invalid policy data JSON: {e}"}, status=400)

        trusted_issuers = data.get("trusted_issuers") or []
        if not isinstance(trusted_issuers, list):
            trusted_issuers = []

        def load(ctx):
            rego_modules = []
            for tid in policy_template_ids:
                tpl = registry_client.get_policy_template(tid)
                source = (tpl.get("rego_source") or "").strip()
                if not source:
                    raise ValueError(
                        f"Policy '{tpl.get('name', tid)}' has no rego source."
                    )
                rego_modules.append([tpl["name"], source])
            meta = (registry_client.get_asset_by_did(did) or {}).get(
                "metadata", {}
            ) or {}
            host, port = meta.get("guardian_url", ""), meta.get("guardian_port", "")
            if not host or not port:
                raise ValueError("Guardian URL/port missing on this asset.")
            ctx["rego_modules"] = rego_modules
            ctx["guardian"] = _guardian_url_port(host, port)
            ctx["asset_name"] = meta.get("name") or _short_id(contract_id)
            return {"detail": f"{len(rego_modules)} policy(ies)"}

        def create_policy(ctx):
            result = pdo_runner.create_asset_policy(
                f"Policy for {ctx['asset_name']}",
                ctx["guardian"],
                user_name,
                ctx["rego_modules"],
            )
            ctx["policy_id"] = result["policy_contract_id"]
            ctx["token_id"] = result["token_contract_id"]

        def set_data(ctx):
            if not policy_data:
                raise SkipStep("no policy data provided")
            pdo_runner.set_policy_data(ctx["policy_id"], policy_data, user_name)

        def update_registry(ctx):
            registry_client.update_asset_metadata_by_did(
                did,
                {"policy_contract": make_did(ctx["token_id"]), "policy_data": policy_data},
            )

        def register_issuers(ctx):
            entries = [
                e
                for e in trusted_issuers
                if isinstance(e, dict)
                and (e.get("did") or "").strip()
                and (e.get("credential_types") or [])
            ]
            if not entries:
                raise SkipStep("none provided")
            errors = []
            for entry in entries:
                entry_did = entry["did"].strip()
                try:
                    issuer_contract_id, issuer_path = parse_did(entry_did)
                    pdo_runner.register_policy_trusted_issuer(
                        ctx["policy_id"],
                        issuer_contract_id,
                        user_name,
                        path=[issuer_path] if issuer_path else [],
                        credential_types=entry["credential_types"],
                    )
                except Exception as e:
                    logger.exception("Failed to register trusted issuer %s", entry_did)
                    errors.append(f"{entry_did}: {e}")
            if errors:
                return {"detail": "some issuers failed: " + "; ".join(errors)}
            return {"detail": f"{len(entries)} issuer(s)"}

        steps = [
            ("load", "Loading the selected policies", load),
            ("policy", "Creating the policy and token contracts", create_policy),
            ("data", "Setting the policy data", set_data),
            ("registry", "Updating the asset registry", update_registry),
            ("issuers", "Registering trusted issuers", register_issuers),
        ]
        return stream_steps(
            steps,
            complete=lambda ctx: {
                "redirect": dashboard_url,
                "message": "Asset exposed via rego policy.",
            },
        )


class AssetUseStreamView(BaseView):
    """POST {asset_did, wallet_id} — run the consumer download flow and decrypt,
    streaming progress. The decrypted data is returned on the terminal event as
    ``result.data``. JS variant of :class:`AssetUseEndpoint`."""

    http_method_names = ["post"]

    def post(self, request):
        data = _json_body(request)
        asset_did = (data.get("asset_did") or "").strip()
        wallet_id = (data.get("wallet_id") or "").strip()
        if not asset_did or not wallet_id:
            return JsonResponse(
                {"error": "asset_did and wallet_id are required"}, status=400
            )

        user_name = AppConfig.get_instance().public_key
        if not ledger_client.user_owns_contract(user_name, wallet_id):
            return JsonResponse({"error": f"wallet not found: {wallet_id}"}, status=400)

        try:
            asset_info = registry_client.get_asset_by_did(asset_did)
        except Exception as e:
            return JsonResponse({"error": f"failed to look up asset: {e}"}, status=400)
        metadata = (asset_info or {}).get("metadata", {}) or {}
        token_did = metadata.get("policy_contract", "")
        if not token_did:
            return JsonResponse(
                {"error": "Asset has not been exposed (no policy_contract)."},
                status=400,
            )
        token_id, _ = parse_did(token_did)
        guardian = _guardian_url_port(
            metadata.get("guardian_url", ""), metadata.get("guardian_port", "")
        )

        def download(ctx):
            output_path, _ = pdo_runner.use_asset(
                wallet_id=wallet_id,
                token_id=token_id,
                guardian_url_port=guardian,
                user_name=user_name,
            )
            ctx["output_path"] = output_path

        def decrypt(ctx):
            ctx["data"] = channel_keys.decrypt_download(user_name, ctx["output_path"])

        steps = [
            ("download", "Requesting and downloading the data", download),
            ("decrypt", "Decrypting with your channel key", decrypt),
        ]
        return stream_steps(
            steps,
            complete=lambda ctx: {
                "result": {"data": ctx.get("data", "")},
                "message": "Data downloaded and decrypted.",
            },
        )
