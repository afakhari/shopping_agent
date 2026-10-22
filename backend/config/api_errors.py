"""Stable public error envelope for DRF endpoints."""
from __future__ import annotations

from rest_framework.views import exception_handler


_MESSAGES = {
    400: ("VALIDATION_ERROR", "پارامترهای ورودی معتبر نیستند."),
    401: ("UNAUTHENTICATED", "برای این درخواست احراز هویت لازم است."),
    403: ("FORBIDDEN", "اجازه انجام این درخواست وجود ندارد."),
    404: ("NOT_FOUND", "مورد درخواستی پیدا نشد."),
    405: ("METHOD_NOT_ALLOWED", "این روش برای endpoint پشتیبانی نمی‌شود."),
    429: ("RATE_LIMITED", "تعداد درخواست‌ها بیش از حد مجاز است."),
    503: ("DEPENDENCY_UNAVAILABLE", "یکی از سرویس‌های موردنیاز در دسترس نیست."),
}


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None
    code, message = _MESSAGES.get(
        response.status_code,
        ("INTERNAL_ERROR", "در پردازش درخواست خطایی رخ داد."),
    )
    details = response.data
    response.data = {
        "error": {
            "code": code,
            "message": message,
            "details": details if response.status_code < 500 else None,
            "request_id": (
                context.get("request").headers.get("X-Request-ID")
                if context.get("request") else None
            ),
        }
    }
    return response
