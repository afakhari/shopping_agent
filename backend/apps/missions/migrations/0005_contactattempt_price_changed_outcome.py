"""Add explicit price-changed outcome without inventing new price values."""
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("missions", "0004_contactattempt_retry_snapshot")]
    operations = [
        migrations.AlterField(
            model_name="contactattempt",
            name="outcome",
            field=models.CharField(
                max_length=32,
                choices=[
                    ("confirmed_available", "موجودی تأیید شد"),
                    ("unavailable", "ناموجود"),
                    ("no_answer", "بدون پاسخ"),
                    ("closed", "بسته"),
                    ("error", "خطا"),
                    ("price_changed", "تغییر قیمت گزارش‌شده در شبیه‌سازی"),
                ],
            ),
        ),
    ]
