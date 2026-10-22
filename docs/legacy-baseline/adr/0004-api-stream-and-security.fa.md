# ADR-0004 — API، رویدادها و ایمنی ابزارها

- وضعیت: پذیرفته‌شده
- تاریخ: 2026-10-21

## تصمیم

- API version prefix `/api/v1/`.
- search/filter از HTTP JSON و بدون LLM.
- mission turn از POST و stream با `fetch`؛ SSE فقط اگر پشتبان proxy و deploy تأیید شود.
- event schema دارای version و sequence.
- مبلغ در JSON به‌صورت string؛ خطاها با envelope مشترک.
- تمام ورودی/خروجی validate؛ tool whitelist؛ timeout برای provider خارجی.
- تماس پیش‌فرض simulator server-side؛ client نمی‌تواند نتیجه تماس را تعیین کند.
- CORS محدود، secrets فقط server-side، log بدون API key و بدون reasoning مخفی.

## دلیل

مسیر عمده یک‌طرفه و مرحله‌ای است؛ WebSocket در نسخه اولیه ارزش اضافی کافی ندارد. قرارداد اختصاصی کوچک تعداد وابستگی‌ها را کاهش می‌دهد.

## پیامدها

برای refresh/reconnect، snapshot مأموریت لازم است. sequence جلوی overwrite ناشی از event تکراری/قدیمی را می‌گیرد. اگر انتقال stream در میزبان ناپایدار باشد، fallback به poll snapshot قابل پیاده‌سازی است.
