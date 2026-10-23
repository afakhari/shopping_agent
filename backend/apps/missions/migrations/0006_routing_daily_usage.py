"""Shared paid-routing usage cap, default-disabled until operational approval."""
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("missions", "0005_contactattempt_price_changed_outcome")]
    operations = [
        migrations.CreateModel(
            name="RoutingDailyUsage",
            fields=[
                ("day", models.DateField(primary_key=True, serialize=False)),
                ("requests", models.PositiveIntegerField(default=0)),
            ],
            options={"db_table": "mission_routing_daily_usage"},
        ),
    ]
