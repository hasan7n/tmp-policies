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
