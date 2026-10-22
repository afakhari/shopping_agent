# Initial schema for missions, events, and the controlled contact simulator.
import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [("catalog", "0003_shop_in_person_credit_flag")]
    operations = [
        migrations.CreateModel(
            name="PurchaseMission",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("initial_message", models.TextField(max_length=2000)),
                ("status", models.CharField(choices=[("created", "ایجاد شده"), ("active", "در حال اجرا"), ("waiting_for_user", "در انتظار کاربر"), ("completed", "تکمیل شده"), ("failed", "ناموفق")], default="created", max_length=32)),
                ("current_stage", models.CharField(default="created", max_length=80)),
                ("constraints", models.JSONField(blank=True, default=dict)),
                ("state", models.JSONField(blank=True, default=dict)),
                ("client_request_id", models.CharField(blank=True, max_length=100, null=True)),
                ("last_event_seq", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "purchase_mission", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="ContactAttempt",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("purpose", models.CharField(choices=[("verify_availability", "بررسی موجودی"), ("verify_price", "بررسی قیمت"), ("verify_hours", "بررسی ساعت کاری")], max_length=32)),
                ("outcome", models.CharField(choices=[("confirmed_available", "موجودی تأیید شد"), ("unavailable", "ناموجود"), ("no_answer", "بدون پاسخ"), ("closed", "بسته"), ("error", "خطا")], max_length=32)),
                ("source_type", models.CharField(default="demo_simulation", max_length=32)),
                ("scenario_index", models.PositiveIntegerField(default=0)),
                ("response_text", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("mission", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="contact_attempts", to="missions.purchasemission")),
                ("offer", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="contact_attempts", to="catalog.offer", to_field="source_id")),
                ("shop", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="contact_attempts", to="catalog.shop", to_field="source_id")),
            ],
            options={"db_table": "purchase_contact_attempt", "ordering": ["created_at", "id"]},
        ),
        migrations.CreateModel(
            name="MissionEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("seq", models.PositiveIntegerField()),
                ("event_type", models.CharField(max_length=64)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("mission", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="events", to="missions.purchasemission")),
            ],
            options={"db_table": "purchase_mission_event", "ordering": ["seq"]},
        ),
        migrations.AddIndex(model_name="purchasemission", index=models.Index(fields=["status", "updated_at"], name="mission_status_updated_idx")),
        migrations.AddConstraint(model_name="missionevent", constraint=models.UniqueConstraint(fields=("mission", "seq"), name="mission_event_seq_uniq")),
        migrations.AddIndex(model_name="missionevent", index=models.Index(fields=["mission", "created_at"], name="mission_event_time_idx")),
        migrations.AddIndex(model_name="contactattempt", index=models.Index(fields=["mission", "created_at"], name="contact_mission_time_idx")),
        migrations.AddIndex(model_name="contactattempt", index=models.Index(fields=["shop", "outcome"], name="contact_shop_outcome_idx")),
    ]
