import json
import logging

from django.shortcuts import get_object_or_404, render

from .. import pdo_runner, registry_client
from ..did_utils import make_did, parse_did
from ..models import AppConfig, Entity
from ._helpers import BaseView, JsonView, redirect_with_msg, require

logger = logging.getLogger(__name__)


# ============================================================
# Page views (server-rendered)
# ============================================================
class WalletsListView(BaseView):
    """GET: list wallets. POST: create a new wallet (single primary action)."""

    def get(self, request):
        wallets = Entity.objects.filter(entity_type='WALLET').order_by('pk')
        return render(request, 'wallets/list.html', {'wallets': wallets})

    def post(self, request):
        name = (request.POST.get('name') or '').strip()
        if not name:
            return redirect_with_msg('/wallets/', 'Wallet name is required.', 'error')

        user_name = AppConfig.get_instance().public_key
        try:
            contract_id = pdo_runner.create_wallet(name, user_name)
        except Exception as e:
            logger.exception("Failed to create wallet")
            return redirect_with_msg('/wallets/', f'Failed to create wallet: {e}', 'error')

        Entity.objects.create(
            did=make_did(contract_id),
            name=name,
            entity_type='WALLET',
            contract_name=f'identity.{name}.signature_authority',
            owner_key=user_name,
            extra_data={'signing_contexts': []},
        )
        return redirect_with_msg('/wallets/', f'Wallet "{name}" created.', 'success')


class WalletDetailView(BaseView):
    """GET-only: render the wallet dashboard. All mutating actions are JSON
    endpoints (see ``api.py``)."""

    def get(self, request, pk):
        wallet = get_object_or_404(Entity, pk=pk, entity_type='WALLET')
        user_name = AppConfig.get_instance().public_key

        vcs, vcs_error = {}, None
        try:
            contract_id, _ = parse_did(wallet.did)
            vcs = pdo_runner.wallet_list_vcs(contract_id, user_name)
        except Exception as e:
            logger.exception("Failed to list wallet VCs")
            vcs_error = str(e)

        templates, templates_error = [], None
        try:
            templates = registry_client.list_credential_templates()
        except Exception as e:
            logger.exception("Failed to fetch credential templates")
            templates_error = str(e)

        return render(request, 'wallets/detail.html', {
            'entity': wallet,
            'signing_contexts': wallet.signing_contexts,
            'vcs': vcs,
            'vcs_error': vcs_error,
            'templates': templates,
            'templates_error': templates_error,
        })


# ============================================================
# JSON endpoints (one logical action each)
# ============================================================
def _get_wallet(pk):
    return get_object_or_404(Entity, pk=pk, entity_type='WALLET')


class WalletAddVCEndpoint(JsonView):
    """POST {vc: {...}} — store a VC in the wallet."""

    def handle(self, request, data, pk):
        wallet = _get_wallet(pk)
        vc = require(data, 'vc')
        if not isinstance(vc, dict):
            raise ValueError("'vc' must be a JSON object")

        contract_id, _ = parse_did(wallet.did)
        pdo_runner.wallet_add_vc(
            contract_id, vc, AppConfig.get_instance().public_key)
        return {'ok': True, 'message': 'Credential added.'}


class WalletRegisterIssuerEndpoint(JsonView):
    """POST {name, description?, extensible?} — register a signing context."""

    def handle(self, request, data, pk):
        wallet = _get_wallet(pk)
        name = require(data, 'name')
        description = (data.get('description') or '').strip() or f'issuer {name}'
        extensible = bool(data.get('extensible', False))

        existing = {tuple(c.get('path', [])) for c in wallet.signing_contexts}
        if (name,) in existing:
            raise ValueError(f"signing context {name!r} already registered")

        contract_id, _ = parse_did(wallet.did)
        pdo_runner.register_signing_context(
            contract_id,
            AppConfig.get_instance().public_key,
            path=[name],
            description=description,
            extensible=extensible,
        )

        ctxs = list(wallet.signing_contexts)
        ctxs.append({'path': [name], 'description': description, 'extensible': extensible})
        wallet.extra_data['signing_contexts'] = ctxs
        wallet.save(update_fields=['extra_data'])

        return {
            'ok': True,
            'message': f'Issuer "{name}" registered.',
            'issuer': {
                'did': make_did(contract_id, name),
                'path': [name],
                'description': description,
                'extensible': extensible,
            },
        }


class WalletSignCredentialEndpoint(JsonView):
    """POST {signing_context, template_type, subject_did, claims} — sign a VC.

    Returns the signed VC JSON on success.
    """

    def handle(self, request, data, pk):
        wallet = _get_wallet(pk)
        signing_context, template_type, subject_did = require(
            data, 'signing_context', 'template_type', 'subject_did')
        claims = data.get('claims') or {}
        if not isinstance(claims, dict):
            raise ValueError("'claims' must be a JSON object")

        known_paths = {tuple(c.get('path', [])) for c in wallet.signing_contexts}
        if (signing_context,) not in known_paths:
            raise ValueError(
                f"signing context {signing_context!r} not registered on this wallet")

        sa_contract_id, _ = parse_did(wallet.did)
        subject_contract_id, _ = parse_did(subject_did)
        credential = {
            'type': [template_type],
            'issuer': {'id': make_did(sa_contract_id, signing_context)},
            'credentialSubject': {'id': subject_contract_id, 'claims': claims},
        }

        signed_vc = pdo_runner.sign_credential(
            sa_contract_id,
            signing_context_path=[signing_context],
            credential_dict=credential,
            user_name=AppConfig.get_instance().public_key,
        )
        return {'ok': True, 'signed_vc': signed_vc}
