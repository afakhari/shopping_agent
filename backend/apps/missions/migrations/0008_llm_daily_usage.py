"""Shared global daily ceiling for BoxAPI / OpenAI-compatible calls."""
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("missions", "0007_turn_lease_and_mission_request_uniq")]
    operations = [
        migrations.CreateModel(
            name="LLMDailyUsage",
            fields=[
                ("day", models.DateField(primary_key=True, serialize=False)),
                ("requests", models.PositiveIntegerField(default=0)),
            ],
            options={"db_table": "mission_llm_daily_usage"},
        ),
    ]
