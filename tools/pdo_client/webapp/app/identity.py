"""
Public key / identity abstraction layer.
The current identity is the public_key field of the singleton AppConfig.
"""

import logging
import os

from django.conf import settings

from .models import AppConfig

logger = logging.getLogger(__name__)

_KEY_SUFFIX = "_private.pem"


def get_current_identity():
    """Return the current public key (username) or empty string."""
    return AppConfig.get_instance().public_key


def list_available_identities():
    """Return the identities that have keys in USER_KEYS_FOLDER, sorted.

    PDO user keys are named ``<name>_private.pem``; the base name is the
    identity used to sign. Returns an empty list if the folder is missing.
    """
    try:
        names = [
            fname[: -len(_KEY_SUFFIX)]
            for fname in os.listdir(settings.USER_KEYS_FOLDER)
            if fname.endswith(_KEY_SUFFIX)
        ]
    except OSError:
        return []
    return sorted(names)


def set_current_identity(public_key):
    """Set the current identity (public key / username)."""
    config = AppConfig.get_instance()
    config.public_key = public_key
    config.save(update_fields=["public_key"])


def ensure_provisioned(user_name):
    """Give a user a wallet and a channel key if they don't have them yet.

    Called when the identity is switched, so a user is ready to use without any
    manual setup. Idempotent (skips whatever already exists) and best-effort —
    failures are logged but never block the switch.
    """
    if not user_name:
        return

    # Imported lazily: pdo_runner pulls in the heavy pdo.* stack, and this module
    # is imported on every request (context processor).
    from . import channel_keys, ledger_client, pdo_runner

    try:
        if not ledger_client.list_signature_authority_ids(user_name):
            pdo_runner.create_wallet("wallet", user_name)
    except Exception:
        logger.exception("Failed to ensure a wallet for %s", user_name)

    try:
        if not channel_keys.has_channel_key(user_name):
            channel_keys.generate(user_name)
    except Exception:
        logger.exception("Failed to ensure a channel key for %s", user_name)


def is_configured():
    return bool(get_current_identity())
