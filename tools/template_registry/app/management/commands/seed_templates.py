"""Seed the template registry from files on disk.

Credential templates come from the ``credentials/`` folder (one JSON Schema per
credential) and policy templates come from the ``duos/`` folder (one subfolder
per DUO). The command reads everything it needs from those folders, so adding a
credential schema or a DUO -- or editing a rego module, its README, or its
policy data schema -- is picked up simply by re-running it. It is idempotent
(``update_or_create`` keyed on the natural unique field).

    python manage.py seed_templates
"""

import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from app.models import CredentialTemplate, PolicyTemplate

CREDENTIALS_DIR = Path(settings.BASE_DIR) / "credentials"
DUOS_DIR = Path(settings.BASE_DIR) / "duos"

CREDENTIAL_SUFFIX = ".schema.json"


def _simplify(properties):
    """Project a JSON Schema ``properties`` object into a flat claims template
    (``{name: type-or-nested}``) usable as a fill-in hint when signing a VC."""
    out = {}
    for name, spec in (properties or {}).items():
        if not isinstance(spec, dict):
            out[name] = "string"
            continue
        kind = spec.get("type")
        if kind == "object" and "properties" in spec:
            out[name] = _simplify(spec["properties"])
        elif kind == "array":
            item_type = (spec.get("items") or {}).get("type", "string")
            out[name] = [item_type]
        else:
            out[name] = kind or "string"
    return out


class Command(BaseCommand):
    help = (
        "Seed credential templates (from credentials/) and policy templates "
        "(from duos/)."
    )

    def handle(self, *args, **options):
        self._seed_credentials()
        self._seed_policies()
        self.stdout.write(self.style.SUCCESS("Template registry seeded."))

    def _seed_credentials(self):
        count = 0
        for path in sorted(CREDENTIALS_DIR.glob(f"*{CREDENTIAL_SUFFIX}")):
            schema = json.loads(path.read_text())
            template_type = schema.get("$id") or path.name[: -len(CREDENTIAL_SUFFIX)]
            CredentialTemplate.objects.update_or_create(
                template_type=template_type,
                defaults={"claims_schema": _simplify(schema.get("properties", {}))},
            )
            self.stdout.write(f"  credential template: {template_type}")
            count += 1
        self.stdout.write(f"seeded {count} credential template(s)")

    def _seed_policies(self):
        count = 0
        for duo_dir in sorted(p for p in DUOS_DIR.iterdir() if p.is_dir()):
            rego_path = duo_dir / "policy.rego"
            if not rego_path.exists():
                continue  # not a DUO module folder

            readme_path = duo_dir / "README.md"
            schema_path = duo_dir / "policy_data_schema.json"
            PolicyTemplate.objects.update_or_create(
                name=duo_dir.name.upper(),
                defaults={
                    "rego_source": rego_path.read_text(),
                    "readme": readme_path.read_text() if readme_path.exists() else "",
                    "policy_data_schema": (
                        json.loads(schema_path.read_text())
                        if schema_path.exists()
                        else {}
                    ),
                },
            )
            self.stdout.write(f"  policy template: {duo_dir.name.upper()}")
            count += 1
        self.stdout.write(f"seeded {count} policy template(s)")
