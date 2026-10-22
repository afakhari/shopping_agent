# قرارداد پیشنهادی API v1

این سند هدف است و تضمین نمی‌کند در نسخه فعلی backend تمام endpointها موجود باشند. اجرای contract test الزامی است.

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
