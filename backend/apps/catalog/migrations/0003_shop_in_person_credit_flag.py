"""Index the hard in-person credit filter and backfill it from source JSON."""
from django.db import migrations, models


def backfill_credit_flag(apps, schema_editor):
    Shop = apps.get_model("catalog", "Shop")
    alias = schema_editor.connection.alias
    batch = []
    shops = Shop.objects.using(alias).all().only("source_id", "payment_options")
    for shop in shops.iterator(chunk_size=1000):
        options = shop.payment_options
        shop.accepts_in_person_credit = isinstance(options, list) and any(
            isinstance(option, dict) and option.get("channel") == "in_person"
            for option in options
        )
        batch.append(shop)
        if len(batch) >= 1000:
            Shop.objects.using(alias).bulk_update(
                batch, ["accepts_in_person_credit"], batch_size=1000
            )
            batch.clear()
    if batch:
        Shop.objects.using(alias).bulk_update(batch, ["accepts_in_person_credit"], batch_size=1000)


def noop_reverse(apps, schema_editor):
    # The derived flag can be dropped with the schema field; source JSON remains intact.
    pass


class Migration(migrations.Migration):
    dependencies = [("catalog", "0002_optional_trigram_index")]
    operations = [
        migrations.AddField(
            model_name="shop",
            name="accepts_in_person_credit",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.RunPython(backfill_credit_flag, noop_reverse),
    ]
