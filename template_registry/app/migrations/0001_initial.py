from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='PolicyTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('policy_data_schema', models.JSONField(default=dict)),
            ],
        ),
        migrations.CreateModel(
            name='CredentialTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('template_type', models.CharField(max_length=100, unique=True)),
                ('claims_keys', models.JSONField()),
            ],
        ),
    ]
