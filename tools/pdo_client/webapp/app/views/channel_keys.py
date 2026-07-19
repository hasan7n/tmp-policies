import logging

from .. import channel_keys
from ..models import AppConfig
from ._helpers import JsonView

logger = logging.getLogger(__name__)


class ChannelKeyGenerateEndpoint(JsonView):
    """POST — generate a channel key for the current user and return its public
    key. Stored under ``settings.CHANNEL_KEYS_DIR/<user_name>/``.
    """

    def handle(self, request, data):
        user_name = AppConfig.get_instance().public_key
        public_key = channel_keys.generate(user_name)
        return {
            "ok": True,
            "message": "Channel key generated.",
            "public_key": public_key,
        }
