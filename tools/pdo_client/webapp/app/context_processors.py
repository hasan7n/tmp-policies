import json

from . import channel_keys, identity
from .models import AppConfig


def app_context(request):
    config = AppConfig.get_instance()
    user_name = config.public_key
    public_key = channel_keys.public_key_pem(user_name)
    return {
        "app_config": config,
        "current_identity": user_name,
        "available_identities": identity.list_available_identities(),
        "has_channel_key": channel_keys.has_channel_key(user_name),
        "channel_public_key": public_key,
        # The public key JSON-escaped (newlines as \n, no surrounding quotes) so
        # it can be pasted straight into a credential's "key" field.
        "channel_public_key_escaped": (
            json.dumps(public_key)[1:-1] if public_key else ""
        ),
    }
