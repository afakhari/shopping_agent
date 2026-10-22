# Generated as an explicit, reviewable initial schema for the project.
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="Product",
            fields=[
                ("source_id", models.CharField(max_length=64, primary_key=True, serialize=False)),
                ("persian_title", models.CharField(blank=True, default="", max_length=1200)),
                (
                    "normalized_title",
                    models.CharField(blank=True, db_index=True, default="", max_length=1200),
                ),
                ("brand_name", models.CharField(blank=True, max_length=300, null=True)),
                ("category_name", models.CharField(blank=True, max_length=500, null=True)),
                ("model", models.CharField(blank=True, max_length=500, null=True)),
                ("specs", models.JSONField(blank=True, default=list)),
                ("image_urls", models.JSONField(blank=True, default=list)),
            ],
            options={"db_table": "catalog_product", "ordering": ["persian_title", "source_id"]},
        ),
        migrations.CreateModel(
            name="Shop",
            fields=[
                ("source_id", models.CharField(max_length=64, primary_key=True, serialize=False)),
                ("name", models.CharField(blank=True, default="", max_length=500)),
                ("category_names", models.JSONField(blank=True, default=list)),
                ("address", models.TextField(blank=True, null=True)),
                ("location_label", models.CharField(blank=True, max_length=300, null=True)),
                ("lat", models.FloatField(blank=True, null=True)),
                ("lon", models.FloatField(blank=True, null=True)),
                ("contacts", models.JSONField(blank=True, default=list)),
                ("payment_options", models.JSONField(blank=True, default=list)),
                ("weekly_hours", models.JSONField(blank=True, default=dict)),
                ("website_url", models.CharField(blank=True, max_length=2048, null=True)),
                ("instagram", models.CharField(blank=True, max_length=2048, null=True)),
                ("supports_fast_delivery", models.BooleanField(blank=True, null=True)),
            ],
            options={"db_table": "catalog_shop", "ordering": ["name", "source_id"]},
        ),
        migrations.CreateModel(
            name="Offer",
            fields=[
                ("source_id", models.CharField(max_length=64, primary_key=True, serialize=False)),
                (
                    "price_toman",
                    models.DecimalField(blank=True, decimal_places=0, max_digits=30, null=True),
                ),
                ("last_price_changed_at", models.DateTimeField(blank=True, null=True)),
                ("seller_title", models.CharField(blank=True, max_length=1200, null=True)),
                ("description", models.TextField(blank=True, null=True)),
                ("warranty", models.JSONField(blank=True, null=True)),
                (
                    "product",
                    models.ForeignKey(
                        db_column="product_id",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="offers",
                        to="catalog.product",
                        to_field="source_id",
                    ),
                ),
                (
                    "shop",
                    models.ForeignKey(
                        db_column="shop_id",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="offers",
                        to="catalog.shop",
                        to_field="source_id",
                    ),
                ),
            ],
            options={"db_table": "catalog_offer", "ordering": ["source_id"]},
        ),
        migrations.AddIndex(
            model_name="product",
            index=models.Index(fields=["category_name"], name="product_category_idx"),
        ),
        migrations.AddIndex(
            model_name="product",
            index=models.Index(fields=["brand_name"], name="product_brand_idx"),
        ),
        migrations.AddIndex(
            model_name="shop",
            index=models.Index(fields=["lat", "lon"], name="shop_coords_idx"),
        ),
        migrations.AddIndex(
            model_name="shop",
            index=models.Index(fields=["location_label"], name="shop_location_idx"),
        ),
        migrations.AddIndex(
            model_name="offer",
            index=models.Index(fields=["product", "price_toman"], name="offer_prod_price_idx"),
        ),
        migrations.AddIndex(
            model_name="offer",
            index=models.Index(fields=["shop", "price_toman"], name="offer_shop_price_idx"),
        ),
        migrations.AddIndex(
            model_name="offer",
            index=models.Index(fields=["last_price_changed_at"], name="offer_price_changed_idx"),
        ),
    ]
