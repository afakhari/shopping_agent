"""Relational representation of the supplied product, shop and offer CSV files."""
from __future__ import annotations

from django.db import models


def has_in_person_credit(payment_options: object) -> bool:
    """Return whether the structured payment options explicitly declare in-person credit."""
    return isinstance(payment_options, list) and any(
        isinstance(option, dict) and option.get("channel") == "in_person"
        for option in payment_options
    )


class Product(models.Model):
    """A base product; independent from any specific shop offer."""

    source_id = models.CharField(primary_key=True, max_length=64)
    persian_title = models.CharField(max_length=1200, blank=True, default="")
    normalized_title = models.CharField(max_length=1200, blank=True, default="", db_index=True)
    brand_name = models.CharField(max_length=300, null=True, blank=True)
    category_name = models.CharField(max_length=500, null=True, blank=True)
    model = models.CharField(max_length=500, null=True, blank=True)
    specs = models.JSONField(default=list, blank=True)
    image_urls = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "catalog_product"
        ordering = ["persian_title", "source_id"]
        indexes = [
            models.Index(fields=["category_name"], name="product_category_idx"),
            models.Index(fields=["brand_name"], name="product_brand_idx"),
        ]

    def __str__(self) -> str:
        return self.persian_title or self.source_id


class Shop(models.Model):
    """A physical shop supplied in the challenge dataset (dataset scope: Tehran)."""

    source_id = models.CharField(primary_key=True, max_length=64)
    name = models.CharField(max_length=500, blank=True, default="")
    category_names = models.JSONField(default=list, blank=True)
    address = models.TextField(null=True, blank=True)
    location_label = models.CharField(max_length=300, null=True, blank=True)
    lat = models.FloatField(null=True, blank=True)
    lon = models.FloatField(null=True, blank=True)
    contacts = models.JSONField(default=list, blank=True)
    payment_options = models.JSONField(default=list, blank=True)
    accepts_in_person_credit = models.BooleanField(default=False, db_index=True)
    weekly_hours = models.JSONField(default=dict, blank=True)
    website_url = models.CharField(max_length=2048, null=True, blank=True)
    instagram = models.CharField(max_length=2048, null=True, blank=True)
    supports_fast_delivery = models.BooleanField(null=True, blank=True)

    class Meta:
        db_table = "catalog_shop"
        ordering = ["name", "source_id"]
        indexes = [
            models.Index(fields=["lat", "lon"], name="shop_coords_idx"),
            models.Index(fields=["location_label"], name="shop_location_idx"),
        ]

    def save(self, *args, **kwargs):
        # Keep the derived filter field in sync when payment_options are being saved.
        # bulk_create() bypasses save(), so the dataset importer sets the value itself.
        update_fields = kwargs.get("update_fields")
        should_update_flag = update_fields is None or bool(
            {"payment_options", "accepts_in_person_credit"} & set(update_fields)
        )
        if should_update_flag:
            self.accepts_in_person_credit = has_in_person_credit(self.payment_options)
            if update_fields is not None:
                kwargs["update_fields"] = set(update_fields) | {"accepts_in_person_credit"}
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name or self.source_id


class Offer(models.Model):
    """A price/listing linking one product to one physical shop."""

    source_id = models.CharField(primary_key=True, max_length=64)
    product = models.ForeignKey(
        Product,
        to_field="source_id",
        db_column="product_id",
        related_name="offers",
        on_delete=models.PROTECT,
    )
    shop = models.ForeignKey(
        Shop,
        to_field="source_id",
        db_column="shop_id",
        related_name="offers",
        on_delete=models.PROTECT,
    )
    # Decimal avoids float rounding and can retain extreme source values for audit.
    price_toman = models.DecimalField(max_digits=30, decimal_places=0, null=True, blank=True)
    last_price_changed_at = models.DateTimeField(null=True, blank=True)
    seller_title = models.CharField(max_length=1200, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    warranty = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "catalog_offer"
        ordering = ["source_id"]
        indexes = [
            models.Index(fields=["product", "price_toman"], name="offer_prod_price_idx"),
            models.Index(fields=["shop", "price_toman"], name="offer_shop_price_idx"),
            models.Index(fields=["last_price_changed_at"], name="offer_price_changed_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.product_id} @ {self.shop_id}"
