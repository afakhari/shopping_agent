from django.contrib import admin

from .models import Offer, Product, Shop


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("source_id", "persian_title", "brand_name", "category_name")
    search_fields = ("source_id", "persian_title", "normalized_title", "brand_name", "model")
    list_filter = ("category_name", "brand_name")
    show_full_result_count = False


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ("source_id", "name", "location_label", "lat", "lon")
    search_fields = ("source_id", "name", "address", "location_label")
    show_full_result_count = False


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = ("source_id", "product", "shop", "price_toman", "last_price_changed_at")
    search_fields = ("source_id", "product__persian_title", "shop__name", "seller_title")
    show_full_result_count = False
