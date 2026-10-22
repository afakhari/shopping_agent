"""Input validation for deterministic catalog search APIs."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from rest_framework import serializers

from apps.catalog.services.normalization import normalize_persian_text


class OfferFilterSerializer(serializers.Serializer):
    max_price_toman = serializers.CharField(required=False, allow_blank=False, max_length=30)
    must_have_in_person_credit = serializers.BooleanField(required=False, default=False)
    lat = serializers.FloatField(required=False, min_value=-90, max_value=90)
    lon = serializers.FloatField(required=False, min_value=-180, max_value=180)
    radius_m = serializers.IntegerField(required=False, min_value=100, max_value=100_000)
    sort = serializers.ChoiceField(
        required=False,
        default="relevance",
        choices=("relevance", "price_asc", "distance_asc", "recent_price_change"),
    )
    page = serializers.IntegerField(required=False, default=1, min_value=1)
    page_size = serializers.IntegerField(required=False, default=20, min_value=1, max_value=50)

    def validate_max_price_toman(self, value: str) -> Decimal:
        normalized = (
            normalize_persian_text(value).replace(",", "").replace("٬", "").replace(" ", "")
        )
        if not normalized.isascii() or not normalized.isdigit():
            raise serializers.ValidationError("سقف بودجه باید عدد صحیح به تومان باشد.")
        try:
            price = Decimal(normalized)
        except InvalidOperation as exc:
            raise serializers.ValidationError("سقف بودجه معتبر نیست.") from exc
        if price < 0 or price >= Decimal("1e30"):
            raise serializers.ValidationError("سقف بودجه خارج از محدوده مجاز است.")
        return price

    def validate(self, attrs):
        has_lat = "lat" in attrs
        has_lon = "lon" in attrs
        if has_lat != has_lon:
            raise serializers.ValidationError({"lat": "lat و lon باید با هم ارسال شوند."})
        if "radius_m" in attrs and not (has_lat and has_lon):
            raise serializers.ValidationError(
                {"radius_m": "برای تعیین شعاع، مختصات lat و lon الزامی است."}
            )
        if attrs.get("sort") == "distance_asc" and not (has_lat and has_lon):
            raise serializers.ValidationError(
                {"sort": "مرتب‌سازی براساس فاصله به مختصات lat و lon نیاز دارد."}
            )
        attrs["normalized_query"] = normalize_persian_text(attrs.get("q", ""))
        return attrs


class ProductSearchSerializer(OfferFilterSerializer):
    q = serializers.CharField(required=True, min_length=1, max_length=200, trim_whitespace=True)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if not attrs["normalized_query"]:
            raise serializers.ValidationError({"q": "عبارت جست‌وجو پس از نرمال‌سازی خالی است."})
        return attrs
