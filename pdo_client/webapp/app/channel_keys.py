"""Per-user channel keys.

A channel key is an RSA key pair a user generates to receive downloaded data:
the guardian encrypts the data with the public key (carried in the user's
public-key credential), and the user decrypts the result with the private key.

Keys live under ``settings.CHANNEL_KEYS_DIR/<user_name>/`` as ``private_key.pem``,
``public_key.pem`` and ``credential_key.json`` (see ``channel_keys_utils``).
"""

import os
import re
import tempfile

from django.conf import settings


def _safe_user(user_name):
    """Filesystem-safe folder name for a user identity."""
    return re.sub(r"[^A-Za-z0-9_.-]", "_", user_name or "") or "unknown"


def user_dir(user_name):
    return os.path.join(settings.CHANNEL_KEYS_DIR, _safe_user(user_name))


def private_key_path(user_name):
    return os.path.join(user_dir(user_name), "private_key.pem")


def public_key_path(user_name):
    return os.path.join(user_dir(user_name), "public_key.pem")


def has_channel_key(user_name):
    """True once the user has generated a channel key."""
    return bool(user_name) and os.path.isfile(private_key_path(user_name))


def public_key_pem(user_name):
    """Return the user's public channel key (PEM text), or '' if none."""
    path = public_key_path(user_name)
    if not os.path.isfile(path):
        return ""
    with open(path) as f:
        return f.read()


def generate(user_name):
    """Generate (or regenerate) the user's channel key pair and public-key
    credential. Returns the public key PEM text.
    """
    from channel_keys_utils.generate_channel_key import (
        generate_credential,
        generate_keys,
    )

    out_dir = user_dir(user_name)
    public_pem_file, _ = generate_keys(out_dir)
    generate_credential(public_pem_file, out_dir)
    return public_key_pem(user_name)


def decrypt_download(user_name, encrypted_path):
    """Decrypt a downloaded (encrypted) file with the user's private channel
    key and return the plaintext as text.
    """
    from channel_keys_utils.read_data import read_data

    fd, decrypted_path = tempfile.mkstemp(
        prefix="channel_dec_", suffix=".bin", dir=settings.SCRATCH_DIR
    )
    os.close(fd)
    try:
        read_data(encrypted_path, private_key_path(user_name), decrypted_path)
        with open(decrypted_path, "rb") as f:
            return f.read().decode(errors="replace")
    finally:
        try:
            os.unlink(decrypted_path)
        except OSError:
            pass
