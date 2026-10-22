from django.urls import path

from apps.search.views import product_detail, product_offers, shop_detail

app_name = "catalog"
urlpatterns = [
    path("products/<str:product_id>/", product_detail, name="product-detail"),
    path("products/<str:product_id>/offers/", product_offers, name="product-offers"),
    path("shops/<str:shop_id>/", shop_detail, name="shop-detail"),
]
