"""
Seeds the database from config/seed_data.json on startup.
All operations are idempotent — safe to call multiple times.
"""

import json
import logging
import os

logger = logging.getLogger(__name__)

SEED_DATA_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'config', 'seed_data.json')
)


def initialize():
    _seed_policy_templates()
    _seed_credential_templates()


def _load_seed_data():
    with open(SEED_DATA_PATH) as f:
        return json.load(f)


def _seed_policy_templates():
    from .models import PolicyTemplate

    data = _load_seed_data()
    for tpl in data.get('policy_templates', []):
        obj, created = PolicyTemplate.objects.get_or_create(
            name=tpl['name'],
            defaults={'policy_data_schema': tpl.get('policy_data_schema', {})},
        )
        if created:
            logger.info("Seeded policy template: %s", tpl['name'])


def _seed_credential_templates():
    from .models import CredentialTemplate

    data = _load_seed_data()
    for tpl in data.get('credential_templates', []):
        obj, created = CredentialTemplate.objects.get_or_create(
            template_type=tpl['template_type'],
            defaults={'claims_keys': tpl['claims_keys']},
        )
        if created:
            logger.info("Seeded credential template: %s", tpl['template_type'])
