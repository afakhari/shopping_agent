"""Versioned API input and output schemas for purchase missions."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from rest_framework import serializers

from apps.catalog.services.normalization import normalize_persian_text


class MissionConstraintsSerializer(serializers.Serializer):
    city = serializers.CharField(required=False, max_length=40)
    max_price_toman = serializers.CharField(required=False, allow_null=True, trim_whitespace=True, max_length=32)
    must_have_in_person_credit = serializers.BooleanField(required=False)
    # Explicit hard requirements, never inferred from vague preferences.
    brand_name = serializers.CharField(required=False, allow_null=True, max_length=300)
    model_exact = serializers.CharField(required=False, allow_null=True, max_length=500)
    lat = serializers.FloatField(required=False, min_value=-90, max_value=90)
    lon = serializers.FloatField(required=False, min_value=-180, max_value=180)
    radius_m = serializers.IntegerField(required=False, min_value=100, max_value=100_000)
    sort = serializers.ChoiceField(
        required=False,
        choices=("relevance", "price_asc", "distance_asc", "recent_price_change"),
    )

    def validate_city(self, value: str) -> str:
        normalized = normalize_persian_text(value)
        if normalized not in {"tehran", "تهران"}:
            raise serializers.ValidationError(
                "در نسخه فعلی، فقط فروشگاه‌های ثبت‌شده تهران پشتیبانی می‌شوند."
            )
        return "tehran"

    def validate_max_price_toman(self, value: str | None) -> str | None:
        # Explicit null means the user intentionally cleared the budget filter.
        if value is None:
            return None
        normalized = normalize_persian_text(value).replace(",", "").replace("٬", "").replace(" ", "")
        if not normalized.isascii() or not normalized.isdigit():
            raise serializers.ValidationError("سقف بودجه باید عدد صحیح به تومان باشد.")
        try:
            amount = Decimal(normalized)
        except InvalidOperation as exc:
            raise serializers.ValidationError("سقف بودجه معتبر نیست.") from exc
        if amount < 0 or amount >= Decimal("1e30"):
            raise serializers.ValidationError("سقف بودجه خارج از محدوده مجاز است.")
        return str(amount.quantize(Decimal("1")))


class MissionCreateSerializer(serializers.Serializer):
    initial_message = serializers.CharField(max_length=2000, trim_whitespace=True)
    constraints = serializers.JSONField(required=False)
    client_request_id = serializers.CharField(required=False, allow_blank=False, max_length=100)

    def validate_initial_message(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("متن اولیه مأموریت نمی‌تواند خالی باشد.")
        return value.strip()

    def validate_constraints(self, value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise serializers.ValidationError("constraints باید یک شیء JSON باشد.")
        serializer = MissionConstraintsSerializer(data=value)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data


class MissionTurnSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=2000, trim_whitespace=True)
    constraints = serializers.JSONField(required=False)
    client_request_id = serializers.CharField(required=False, allow_blank=False, max_length=100)

    def validate_message(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("پیام نمی‌تواند خالی باشد.")
        return value.strip()

    def validate_constraints(self, value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise serializers.ValidationError("constraints باید یک شیء JSON باشد.")
        serializer = MissionConstraintsSerializer(data=value)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data


class ContactAttemptCreateSerializer(serializers.Serializer):
    client_request_id = serializers.CharField(required=False, allow_blank=False, max_length=100)
    shop_id = serializers.CharField(max_length=64)
    offer_id = serializers.CharField(max_length=64)
    purpose = serializers.ChoiceField(
        required=False,
        default="verify_availability",
        choices=("verify_availability",),
    )
    # Stock is the demo outcome; price and hours are separate registered evidence.
    questions = serializers.ListField(
        child=serializers.ChoiceField(choices=("stock", "price", "hours")),
        min_length=1,
        max_length=3,
        required=False,
        default=lambda: ["stock", "price", "hours"],
    )

    def validate_questions(self, values: list[str]) -> list[str]:
        if len(values) != len(set(values)):
            raise serializers.ValidationError("سؤال تکراری در استعلام مجاز نیست.")
        if "stock" not in values:
            raise serializers.ValidationError(
                "در نسخه فعلی نتیجه شبیه‌سازی مربوط به موجودی است؛ سؤال موجودی باید انتخاب شود."
            )
        return values


    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        forbidden = {"outcome", "response_text", "scenario_result", "scenario_index"}
        initial_keys = set(self.initial_data.keys()) if hasattr(self.initial_data, "keys") else set()
        present = forbidden.intersection(initial_keys)
        if present:
            raise serializers.ValidationError(
                {key: "نتیجه استعلام را سرور تعیین می‌کند." for key in sorted(present)}
            )
        return attrs


class MissionFocusSerializer(serializers.Serializer):
    """Explicit, model-free UX actions, scoped to a particular result set."""
    action = serializers.ChoiceField(choices=(
        "select_product", "view_sellers", "view_products", "select_offer",
    ))
    result_set_id = serializers.CharField(max_length=40)
    product_id = serializers.CharField(max_length=64, required=False)
    offer_id = serializers.CharField(max_length=64, required=False)
    offer_ids = serializers.ListField(
        child=serializers.CharField(max_length=64),
        required=False, max_length=24,
    )

    def validate_offer_ids(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError("شناسه آفر تکراری است.")
        return value

    def validate(self, attrs):
        action = attrs["action"]
        if action in ("select_product", "view_sellers") and not attrs.get("product_id"):
            raise serializers.ValidationError({"product_id": "شناسه محصول ضروری است."})
        if action == "select_offer" and not attrs.get("offer_id"):
            raise serializers.ValidationError({"offer_id": "شناسه آفر ضروری است."})
        if action == "view_sellers" and not attrs.get("offer_ids"):
            raise serializers.ValidationError({"offer_ids": "فهرست فروشندگان باید مشخص باشد."})
        return attrs
