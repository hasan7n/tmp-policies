"""Seed initial policy and credential templates.

Idempotent: uses ``update_or_create`` keyed on the natural unique field, so
re-running this migration (or hand-editing rows between migrations) won't
produce duplicates.
"""

import json
import os

from django.db import migrations

SEED_DATA_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "config", "seed_data.json")
)


def _seed(apps, schema_editor):
    PolicyTemplate = apps.get_model("app", "PolicyTemplate")
    CredentialTemplate = apps.get_model("app", "CredentialTemplate")

    with open(SEED_DATA_PATH) as f:
        data = json.load(f)

    for tpl in data.get("policy_templates", []):
        PolicyTemplate.objects.update_or_create(
            name=tpl["name"],
            defaults={"policy_data_schema": tpl.get("policy_data_schema", {})},
        )

    for tpl in data.get("credential_templates", []):
        CredentialTemplate.objects.update_or_create(
            template_type=tpl["template_type"],
            defaults={"claims_keys": tpl["claims_keys"]},
        )


def _unseed(apps, schema_editor):
    PolicyTemplate = apps.get_model("app", "PolicyTemplate")
    CredentialTemplate = apps.get_model("app", "CredentialTemplate")

    with open(SEED_DATA_PATH) as f:
        data = json.load(f)

    PolicyTemplate.objects.filter(
        name__in=[t["name"] for t in data.get("policy_templates", [])]
    ).delete()
    CredentialTemplate.objects.filter(
        template_type__in=[
            t["template_type"] for t in data.get("credential_templates", [])
        ]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("app", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(_seed, _unseed),
    ]
