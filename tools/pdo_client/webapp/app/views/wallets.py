import logging

from django.http import Http404
from django.shortcuts import render

from .. import ledger_client, pdo_runner
from ..did_utils import make_did
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
    """List the user's wallet contract ids (identity.identity contracts)."""
    return ledger_client.list_identity_ids(user_name)


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

        vcs, vcs_error = {}, None
        try:
            vcs = pdo_runner.wallet_list_vcs(contract_id, user_name)
        except Exception as e:
            logger.exception("Failed to list wallet VCs")
            vcs_error = str(e)

        return render(
            request,
            "wallets/detail.html",
            {
                "wallet": wallet,
                "vcs": vcs,
                "vcs_error": vcs_error,
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
