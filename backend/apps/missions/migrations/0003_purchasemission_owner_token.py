"""Bind purchase missions to an anonymous first-party browser session."""
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("missions", "0002_alter_contactattempt_offer_alter_contactattempt_shop")]
    operations = [
        migrations.AddField(
            model_name="purchasemission",
            name="owner_token",
            field=models.CharField(max_length=64, null=True, blank=True, db_index=True),
        ),
    ]
