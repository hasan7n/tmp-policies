import json
import logging

from django.shortcuts import get_object_or_404, redirect, render

from .. import pdo_runner, registry_client
from ..did_utils import make_did, parse_did
from ..models import AppConfig, Entity
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


class AssetsListView(BaseView):
    """GET-only: list all assets in the registry, annotated with local entity info."""

    def get(self, request):
        assets = []
        list_error = None
        try:
            assets = registry_client.list_assets()
            local_map = {e.did: e for e in Entity.objects.filter(entity_type="ASSET")}
            for a in assets:
                e = local_map.get(a["did"])
                a["is_local"] = e is not None
                a["local_pk"] = e.pk if e else None
        except Exception as e:
            logger.exception("Failed to fetch assets")
            list_error = str(e)

        wallets = Entity.objects.filter(entity_type="WALLET").order_by("pk")
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

            Entity.objects.create(
                did=did,
                name=name,
                entity_type="ASSET",
                contract_name=f"identity.{name}.signature_authority",
                owner_key=user_name,
                extra_data={
                    "guardian_url": guardian_url,
                    "guardian_port": guardian_port,
                },
            )

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
                f"{config.asset_registry_url.rstrip('/')}/api/assets/{registry_pk}/"
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

    def get(self, request, pk):
        entity = get_object_or_404(Entity, pk=pk, entity_type="ASSET")
        user_name = AppConfig.get_instance().public_key

        ctx = {
            "entity": entity,
            "wallets": Entity.objects.filter(entity_type="WALLET").order_by("pk"),
            "has_policy": False,
            "policy_contract_id": None,
            "token_contract_id": None,
            "policy_issuers": {},
            "policy_issuers_error": None,
            "templates": [],
            "templates_error": None,
            "expose_result": request.session.pop("last_expose_result", None),
        }

        # Pull the registry record to discover the (token-DID-shaped)
        # policy_contract field, if expose has been run.
        token_did = ""
        try:
            asset = registry_client.get_asset_by_did(entity.did) or {}
            metadata = asset.get("metadata", {}) or {}
            token_did = metadata.get("policy_contract", "")
        except Exception as e:
            logger.exception("Failed to fetch asset from registry")
            ctx["registry_error"] = str(e)

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
                    ctx["policy_issuers"] = pdo_runner.list_policy_trusted_issuers(
                        policy_id, user_name
                    )
                except Exception as e:
                    logger.exception("Failed to list policy trusted issuers")
                    ctx["policy_issuers_error"] = str(e)

        if not ctx["has_policy"]:
            try:
                ctx["templates"] = registry_client.list_policy_templates()
            except Exception as e:
                logger.exception("Failed to fetch policy templates")
                ctx["templates_error"] = str(e)

        return render(request, "assets/dashboard.html", ctx)


class AssetExposeView(BaseView):
    """POST-only now: create policy + token contracts, set policy data, and
    update the registry. The form lives inside the dashboard page; on success
    we redirect back there.
    """

    def get(self, request, pk):
        return redirect("asset_dashboard", pk=pk)

    def post(self, request, pk):
        entity = get_object_or_404(Entity, pk=pk, entity_type="ASSET")
        user_name = AppConfig.get_instance().public_key
        dashboard_url = f"/assets/{pk}/"

        policy_data_raw = (request.POST.get("policy_data") or "").strip()
        try:
            policy_data = json.loads(policy_data_raw) if policy_data_raw else {}
        except json.JSONDecodeError as e:
            return redirect_with_msg(
                dashboard_url, f"Invalid policy data JSON: {e}", "error"
            )

        guardian_host = entity.extra_data.get("guardian_url", "")
        guardian_port = entity.extra_data.get("guardian_port", "")
        if not guardian_host:
            try:
                meta = (registry_client.get_asset_by_did(entity.did) or {}).get(
                    "metadata", {}
                ) or {}
                guardian_host = meta.get("guardian_url", "")
                guardian_port = meta.get("guardian_port", "")
            except Exception:
                pass

        if not guardian_host or not guardian_port:
            return redirect_with_msg(
                dashboard_url, "Guardian URL/port missing on this asset.", "error"
            )

        guardian = _guardian_url_port(guardian_host, guardian_port)

        try:
            result = pdo_runner.create_asset_policy(
                f"Policy for {entity.name}", guardian, user_name
            )

            if policy_data:
                pdo_runner.set_policy_data(
                    result["policy_contract_id"], policy_data, user_name
                )

            entity.extra_data.update(
                {
                    "policy_contract_id": result["policy_contract_id"],
                    "token_contract_id": result["token_contract_id"],
                    "guardian_url": guardian_host,
                    "guardian_port": guardian_port,
                }
            )
            entity.save(update_fields=["extra_data"])

            token_did = make_did(result["token_contract_id"])
            registry_client.update_asset_metadata_by_did(
                entity.did,
                {"policy_contract": token_did, "policy_data": policy_data},
            )

        except Exception as e:
            logger.exception("Failed to expose asset")
            return redirect_with_msg(
                dashboard_url, f"Failed to expose asset: {e}", "error"
            )

        request.session["last_expose_result"] = json.dumps(
            {
                "policy_contract_id": result["policy_contract_id"],
                "token_contract_id": result["token_contract_id"],
                "token_did": token_did,
            },
            indent=2,
        )
        return redirect_with_msg(
            dashboard_url, "Asset exposed via download policy.", "success"
        )


# ============================================================
# JSON endpoints
# ============================================================
class AssetUseEndpoint(JsonView):
    """POST {asset_did, wallet_pk} — run the consumer download flow and
    return ``{output_file, issued_vc}``."""

    def handle(self, request, data, **kwargs):
        asset_did = require(data, "asset_did")
        wallet_pk = require(data, "wallet_pk")

        wallet = get_object_or_404(Entity, pk=wallet_pk, entity_type="WALLET")
        user_name = AppConfig.get_instance().public_key

        asset_info = registry_client.get_asset_by_did(asset_did)
        metadata = asset_info.get("metadata", {}) or {}

        token_did = metadata.get("policy_contract", "")
        if not token_did:
            raise ValidationError(
                "Asset has not been exposed (no policy_contract in registry)."
            )

        token_contract_id, _ = parse_did(token_did)
        wallet_id, _ = parse_did(wallet.did)
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
    """POST {issuer_did, credential_type} — register a signature authority
    (identified by its DID, optionally with a ``#path`` signing context) as
    a trusted issuer of ``credential_type`` on the asset's policy agent.
    """

    def handle(self, request, data, pk):
        entity = get_object_or_404(Entity, pk=pk, entity_type="ASSET")
        user_name = AppConfig.get_instance().public_key

        issuer_did, credential_type = require(data, "issuer_did", "credential_type")

        try:
            issuer_contract_id, issuer_path = parse_did(issuer_did)
        except ValueError as e:
            raise ValidationError(str(e))
        path = [issuer_path] if issuer_path else []

        try:
            asset = registry_client.get_asset_by_did(entity.did) or {}
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
            credential_type=credential_type,
        )
        return {
            "ok": True,
            "message": f'Issuer registered for "{credential_type}".',
        }
