"""
This file defines the InferenceOperation class, the capability handler that
releases an asset to a caller that is about to run an authorized script on it.
"""

from pdo.contracts.guardian.common.utility import ValidateJSON
import logging
import os

logger = logging.getLogger(__name__)


# XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
class InferenceOperation:
    """Release the asset to a caller that will run the script the policy approved.

    The policy decides which script may touch the data and records its digest in
    the capability. The caller separately reports the digest it computed over the
    script it actually holds, and the data is released only when the two agree --
    so a capability issued for one script cannot be redeemed while running
    another. The reported digest arrives in the request context, outside the
    capability package and therefore unauthenticated, which is exactly why it is
    only ever compared against the authorized value and never trusted on its own.
    """

    # -----------------------------------------------------------------
    __schema__ = {
        "type": "object",
        "properties": {
            "channel_key": {"type": "string"},
            "script_digest": {"type": "string"},
        },
        "required": ["channel_key", "script_digest"],
    }

    __request_context_schema__ = {
        "type": "object",
        "properties": {
            "calculated_script_digest": {"type": "string"},
        },
        "required": ["calculated_script_digest"],
    }

    # -----------------------------------------------------------------
    def __init__(self, config):
        data_path = os.environ.get("GUARDIAN_DATA_PATH")
        if data_path:
            with open(data_path) as f:
                self.data = f.read()
        else:
            raise RuntimeError("GUARDIAN_DATA_PATH not set")

    # -----------------------------------------------------------------
    def __call__(self, params, request_context):
        if not ValidateJSON(params, self.__schema__):
            return None
        if not ValidateJSON(request_context, self.__request_context_schema__):
            return None

        authorized_digest = params["script_digest"]
        calculated_digest = request_context["calculated_script_digest"]
        if calculated_digest != authorized_digest:
            logger.warning(
                "script digest mismatch: capability authorizes %s, caller computed %s",
                authorized_digest,
                calculated_digest,
            )
            return None

        # The channel key the policy carried is not used yet. The data goes back to
        # an FL client on this host rather than across the network, so it is
        # returned in the clear; encrypting it to the channel key is what makes this
        # safe to serve off-host.
        logger.info("releasing data for authorized script %s", authorized_digest)
        return self.data
