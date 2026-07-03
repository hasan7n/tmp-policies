"""
Public key / identity abstraction layer.
The current identity is the public_key field of the singleton AppConfig.
"""

import os

from django.conf import settings

from .models import AppConfig

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


def is_configured():
    return bool(get_current_identity())
