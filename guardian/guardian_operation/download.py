"""
This file defines the InvokeApp class, a WSGI interface class for
handling contract method invocation requests.
"""

from pdo.contracts.guardian.common.utility import ValidateJSON
from .utils import AsymmetricEncryption
import logging
import base64

logger = logging.getLogger(__name__)


# XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
class DownloadOperation:
    # -----------------------------------------------------------------
    __schema__ = {
        "type": "object",
        "properties": {
            "channel_key": {"type": "string"},
        },
        "required": ["channel_key"],
    }

    # -----------------------------------------------------------------
    def __init__(self, config):
        # Model Parameters to be used during inference
        self.data = "secret_data"

    def __encrypted_data(self, channel_key):
        # Encrypt the data using the provided channel key

        return AsymmetricEncryption().encrypt(channel_key.encode(), self.data.encode())

    # -----------------------------------------------------------------
    def __call__(self, params):
        if not ValidateJSON(params, self.__schema__):
            return None
        channel_key = params["channel_key"]
        enc_data = self.__encrypted_data(channel_key)

        return base64.b64encode(enc_data).decode()
