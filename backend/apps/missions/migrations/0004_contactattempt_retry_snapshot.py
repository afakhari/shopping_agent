"""Add unique contact retry keys and durable response snapshots."""
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("missions", "0003_purchasemission_owner_token")]
    operations = [
        migrations.AddField(
            model_name="contactattempt",
            name="client_request_id",
            field=models.CharField(max_length=100, null=True, blank=True),
        ),
        migrations.AddField(
            model_name="contactattempt",
            name="response_snapshot",
            field=models.JSONField(default=dict, blank=True),
        ),
        migrations.AddConstraint(
            model_name="contactattempt",
            constraint=models.UniqueConstraint(
                fields=("mission", "client_request_id"), name="contact_attempt_idempotent_uniq"
            ),
        ),
    ]
