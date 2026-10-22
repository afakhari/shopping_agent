# ADR-0003 — مدل داده و موتور جست‌وجو

- وضعیت: پذیرفته‌شده
- تاریخ: 2026-10-21

## زمینه

Snapshot منبع شامل 225,903 product، 6,476 shop و 331,506 offer است؛ روابط داخلی قابل اتصال‌اند. متن فارسی اختلاف نیم‌فاصله/حروف دارد. فیلتر دقیق باید در دیتابیس اجرا شود.

## تصمیم

- PostgreSQL منبع حقیقت.
- source ID هر موجودیت unique و حفظ شود.
- `Offer` entity مستقل باقی بماند؛ dedupe بر اساس product+shop انجام نشود مگر rule مستند داشته باشد.
- JSON source fields برای specs/images/contacts/payment/hours/warranty parse و نگهداری شوند.
- مبلغ Decimal/Numeric؛ API string؛ timestamp timezone-aware.
- جست‌وجوی مرحله اول با normalizer فارسی + PostgreSQL indexes. `pg_trgm` و PostGIS مشروط به پشتیبانی میزبان.
- `Meilisearch` فقط پس از benchmark واقعی؛ vector DB در scope اولیه نیست.
- شروط سخت eligibility قبل از scoring اعمال شوند.

## پیامدها

Importer و گزارش کیفیت لازم است. JSON specs در ابتدا به جدول مجزا برای هر ویژگی تبدیل نمی‌شود؛ فقط در صورت نیاز query مشخص denormalize می‌شود. اعداد benchmark باید ثبت شوند.

## شرایط بازنگری

- جست‌وجوی فارسی پس از tuning نتایج کم‌کیفیت یا latency بالاتر از هدف بدهد.
- query مشخص به ویژگی ساختاری نیاز داشته باشد که JSON indexing برایش کافی نباشد.
