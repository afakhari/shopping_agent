# قرارداد API v1: پیاده‌شده در برابر پیشنهادی | ۲۳ اکتبر ۲۰۲۶

**وضعیت پیاده‌سازی از `backend/config/urls.py` و routeهای Django روی main #25 بررسی شده است.** بخش «API هدف» پایین، *طرح آتی* است، نه نشانی تضمین‌شده.

## Endpointهای موجود در کد فعلی
- `GET /api/v1/health/live/` و `GET /api/v1/health/ready/`؛ readiness شامل وضعیت پیکربندی LLM است، نه تضمین اتصال real-time.
- `GET /api/v1/catalog/search/?q=...&page_size=...` برای جست‌وجوی فیلترشده با Offer معتبر؛ `GET /api/v1/products/{id}/`، `GET /api/v1/products/{id}/offers/`، `GET /api/v1/shops/{id}/`.
- `POST /api/v1/missions/` با `initial_message` و `constraints`، `GET /api/v1/missions/{uuid}/` با نشست مالک.
- `POST /api/v1/missions/{uuid}/turns/` با `message` و `constraints` و پاسخ SSE شامل `user.message`، `assistant.message`، رویداد UI برای خرید واقعی و `turn.completed`. احوال‌پرسی خالص رویداد UI و فراخوانی LLM ندارد.
- `POST /api/v1/missions/{uuid}/contact-attempts/` با `shop_id`، `offer_id`، `client_request_id` (اختیاری در serializer ولی مهم برای تکرار ایمن)، `purpose=verify_availability` و `questions`؛ نتیجه **شبیه‌سازی‌شده**.
- `GET /api/v1/missions/{uuid}/visit-plan/`، بازیابی state برنامه مراجعه بدون ساخت داده جدید.

**موجود نیست یا تضمین نشده:** `POST /api/v1/products/compare/`، `POST /api/v1/route-estimates/`، `GET /api/v1/missions/{id}/events?after_seq=` و cursor pagination/ETag. در نسخه فعلی client داده رویدادها را از snapshot مأموریت بازیابی می‌کند. مقایسه کالا در UI اجرا می‌شود. برای status واقعی [گزارش مرجع](CURRENT-STATUS-2026-10-23.fa.md).

## API هدف/پیشنهادی (الزاماً پیاده نشده)

## Catalog
GET /api/v1/products?q=&category=&brand=&max_price_toman=&limit=&cursor=
GET /api/v1/products/{id}/
POST /api/v1/products/compare/  body: {product_ids: [id, id, id]}

## Shops
GET /api/v1/offers?product_id=&lat=&lng=&radius_km=&credit_only=&sort=
GET /api/v1/shops/{id}/
POST /api/v1/route-estimates/  body: {origin: {lat,lng}, shop_ids: []}

## Missions
POST /api/v1/missions/  body: {text, filters?, location?}
GET /api/v1/missions/{mission_id}/
POST /api/v1/missions/{mission_id}/turns/  body: {text?, action?, payload?, client_request_id}
POST /api/v1/missions/{mission_id}/contact-attempts/  body: {offer_id, questions: [stock,price,hours], client_request_id}
GET /api/v1/missions/{mission_id}/events?after_seq=
GET /api/v1/missions/{mission_id}/visit-plan/

## پاسخ خطا
{error: {code, message, details?, retryable}, request_id}
نمونه code: VALIDATION_ERROR, OUT_OF_COVERAGE, NO_MATCHES, CREDIT_NOT_ELIGIBLE, RATE_LIMITED, CONTACT_UNAVAILABLE, STALE_MISSION_VERSION.

## ضمانت‌های قرارداد
- تمام مبالغ عدد تومان با field *_toman؛ در UI فرمت می‌شود.
- source و observed_at و updated_at برای قیمت یا استعلام روشن باشند.
- offer_id همراه product_id و shop_id و warranty در صورت وجود ارسال شود.
- برای ساعات unknown/unsupported مقدار مشخص باشد، نه open_now=false حدسی.
- مختصات WGS84 و timezone Asia/Tehran.
- cursor pagination و ETag/cache where safe.
- ماموریت نسخه‌دار؛ کلید idempotency برای endpoint اثرگذار اجباری.
- SSE رویداد پیشرفت واقعی؛ snapshot جایگزین امن قطع اتصال.
- contract fixtures باید قبل از تغییر قرارداد از UI/Backend یکسان بمانند.
