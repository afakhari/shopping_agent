# ADR-0005 — دیپلوی و کنترل scope

- وضعیت: پذیرفته‌شده
- تاریخ: 2026-10-21

## تصمیم

- Docker برای نزدیک‌کردن محیط local و deploy.
- هدف اولیه Liara؛ انتخاب نهایی service/plan پس از تست عملی networking، DB extensions، limits، storage و streaming.
- frontend به صورت static build؛ Django API جدا.
- dataset داخل Git یا Docker image قرار نگیرد؛ ingestion روی environment مقصد اجرا و report ثبت شود.
- `DEBUG=false`, `ALLOWED_HOSTS`, CORS و secret management در production.
- هیچ فناوری یا feature تازه‌ای بدون task، معیار پذیرش و دلیل مشخص اضافه نشود.

## پیامدها

نسخه آنلاین باید از صفر یا از migration/import مستند قابل‌بازیابی باشد. دمو باید با fixtureهای سرور اجرا شود و وابسته به local state توسعه‌دهنده نباشد.

## شرط بازنگری

اگر میزبان هدف API streaming، PostGIS یا مسیر import داده را پشتیبانی نکند، کم‌پیچیدگی‌ترین راه جایگزین انتخاب و در ADR ثبت شود.
