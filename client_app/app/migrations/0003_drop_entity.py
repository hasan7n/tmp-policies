from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("app", "0002_unify_issuers_into_wallets"),
    ]

    operations = [
        migrations.DeleteModel(name="Entity"),
    ]
