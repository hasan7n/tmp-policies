from django.db import migrations, models


def drop_issuer_rows(apps, schema_editor):
    Entity = apps.get_model('app', 'Entity')
    Entity.objects.filter(entity_type='ISSUER').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(drop_issuer_rows, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='entity',
            name='entity_type',
            field=models.CharField(
                choices=[('WALLET', 'Wallet'), ('ASSET', 'Asset')],
                max_length=20,
            ),
        ),
    ]
