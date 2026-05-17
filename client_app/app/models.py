from django.db import models


class AppConfig(models.Model):
    """Singleton application configuration."""

    ledger_url = models.CharField(max_length=200, default="http://127.0.0.1:6600")
    asset_registry_url = models.CharField(
        max_length=200, default="http://127.0.0.1:8001"
    )
    template_registry_url = models.CharField(
        max_length=200, default="http://127.0.0.1:8002"
    )
    public_key = models.TextField(default="")  # user identity (username for now)

    @classmethod
    def get_instance(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def is_configured(self):
        return bool(self.public_key)

    def __str__(self):
        return f"AppConfig(pk={self.pk})"


class Entity(models.Model):
    """A PDO contract owned by this client.

    A wallet is a signature_authority contract. Issuers are not a distinct
    entity — they are signing contexts registered inside a wallet, tracked
    locally in ``extra_data['signing_contexts']`` as a list of
    ``{"path": [..], "description": "..", "extensible": bool}`` dicts.

    For ASSET entities, ``extra_data`` additionally holds policy/token
    contract ids and guardian connection info.
    """

    ENTITY_TYPES = [
        ("WALLET", "Wallet"),
        ("ASSET", "Asset"),
    ]

    did = models.CharField(max_length=500, unique=True)
    name = models.CharField(max_length=200)
    entity_type = models.CharField(max_length=20, choices=ENTITY_TYPES)
    contract_name = models.CharField(max_length=200, default="")
    owner_key = models.TextField(default="")

    save_basename = models.CharField(max_length=200, default="")
    save_blob = models.BinaryField(default=b"")

    extra_data = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.entity_type}:{self.name}"

    @property
    def signing_contexts(self):
        """Return the list of signing contexts registered on this wallet."""
        return (
            self.extra_data.get("signing_contexts", [])
            if self.entity_type == "WALLET"
            else []
        )
