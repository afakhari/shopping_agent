"""Single-flight turn leases and concurrency-safe mission creation IDs."""
from django.db import migrations, models
import django.db.models.deletion


def deduplicate_legacy_creation_keys(apps, schema_editor):
    Mission = apps.get_model("missions", "PurchaseMission")
    qs = (Mission.objects.using(schema_editor.connection.alias)
          .exclude(owner_token__isnull=True)
          .exclude(client_request_id__isnull=True)
          .order_by("owner_token", "client_request_id", "created_at", "id"))
    previous_key = None
    for item in qs.iterator(chunk_size=1000):
        key = (item.owner_token, item.client_request_id)
        if key == previous_key:
            Mission.objects.using(schema_editor.connection.alias).filter(pk=item.pk).update(
                client_request_id=None
            )
        previous_key = key


class Migration(migrations.Migration):
    dependencies = [("missions", "0006_routing_daily_usage")]

    operations = [
        migrations.RunPython(deduplicate_legacy_creation_keys, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="purchasemission",
            constraint=models.UniqueConstraint(
                fields=("owner_token", "client_request_id"),
                name="mission_create_request_uniq",
            ),
        ),
        migrations.CreateModel(
            name="TurnLease",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("client_request_id", models.CharField(max_length=100)),
                ("message", models.TextField(max_length=2000)),
                ("request_constraints", models.JSONField(default=dict)),
                ("issued_at", models.DateTimeField()),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("mission", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="turn_leases", to="missions.purchasemission",
                )),
            ],
            options={
                "db_table": "purchase_turn_lease",
                "constraints": [
                    models.UniqueConstraint(
                        fields=("mission", "client_request_id"),
                        name="turn_lease_request_uniq",
                    )
                ],
            },
        ),
    ]
