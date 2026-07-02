from . import channel_keys
from .models import AppConfig


def app_context(request):
    config = AppConfig.get_instance()
    user_name = config.public_key
    return {
        "app_config": config,
        "current_identity": user_name,
        "has_channel_key": channel_keys.has_channel_key(user_name),
        "channel_public_key": channel_keys.public_key_pem(user_name),
    }
