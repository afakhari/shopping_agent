# مسیر انتشار ایمن و آزمون قبل از تحویل | ۲۳ اکتبر ۲۰۲۶

## وضعیت واقعی
- Docker محلی با PostgreSQL و دیتاست کامل بر اساس گزارش ۲۲ اکتبر آزمایش شده است؛ تأیید اجرای نسخه جدید PRهای #15–#19 روی همان دیتاست باید دوباره انجام شود.
- سرور عمومی، دامنه HTTPS، دسترسی Liara و API Key مدل/نقشه در این گزارش در دسترس نیست؛ بنابراین deployment انجام‌شده ادعا نمی‌شود.
- `compose.production.yaml` صرفاً **overlay برای Docker روی میزبان تحت کنترل با HTTPS termination** است، نه manifest آماده لیارا.

## راه‌اندازی امن با Compose
یک فایل `.env` خصوصی کنار `compose.yaml` بسازید و در آن رمز PostgreSQL، `DJANGO_SECRET_KEY` غیرقابل‌حدس، دامنه مجاز و آدرس HTTPS معتبر قرار دهید. **فایل `.env` را commit یا در گفتگو منتشر نکنید.**

```bash
# تنها روی میزبان امن با TLS reverse proxy و دیسک پایدار:
docker compose -f compose.yaml -f compose.production.yaml config --quiet
docker compose -f compose.yaml -f compose.production.yaml up -d --build
docker compose -f compose.yaml -f compose.production.yaml exec -T backend python manage.py verify_dataset --products 225903 --shops 6476 --offers 331506
```

ملاحظات:
- سرویس frontend در compose پایه HTTP داخلی روی پورت `APP_PORT` دارد. HTTPS باید **قبل از** آن توسط reverse proxy معتبر فراهم شود، چون کوکی نشست production دارای `Secure` است. اجرای مستقیم HTTP برای production پذیرفته نیست.
- PostgreSQL روی میزبان کنترل‌شده با Volume پایدار و حداقل دسترسی باشد؛ پورت DB در compose پایه فقط loopback است.
- اطلاعات محیط محلی `DJANGO_SETTINGS_MODULE=config.settings.local` نباید به محیط عمومی منتقل شود. overlay به‌طور صریح `config.settings.production` را اعمال می‌کند.
- اگر از PostgreSQL مدیریت‌شده یا Liara استفاده شود، متغیر اتصال/Volume و راه‌اندازی بر اساس محیط واقعی جداگانه تطبیق داده شود.
- تنظیمات `LLM_API_KEY` و نام مدل باید صرفاً در backend secret manager ذخیره شود. وضعیت `configured` دلیلی بر دریافت پاسخ مدل نیست؛ آزمون `--require-llm` الزامی است.
- هیچ آفر ثبت‌شده‌ای موجودی لحظه‌ای را تضمین نمی‌کند؛ تماس‌ها در نسخه مسابقه شبیه‌سازی هستند.

## آزمون پذیرش و عدم انتشار
۱. آخرین commit و تمامی jobهای CI را بررسی کنید. `browser-journey` روی fixture مصنوعی و `production-compose-config` فقط روی تنظیمات است.
۲. دیتاست ZIP اصلی را در محیط مجاز با `verify_dataset` چک و مسیر `check-golden-path.ps1 -SkipBackendTests -FullJourney` را روی همین commit اجرا کنید.
۳. با درخواست مبهم، مدل دقیق، بودجه/اعتبار، بازبودن نامعلوم، فروشنده بی‌پاسخ و دوباره‌ارسال استعلام مسیر خرید را با داده اصلی بررسی کنید.
۴. URL عمومی را در مرورگر ناشناس و تلفن واقعی با RTL و اندازه‌های ۳۲۰/۳۹۰/۱۴۴۰ باز کنید. نقشه و fallback، تصاویر، SSE، refresh مأموریت، rate limiting و XSS را بررسی کنید.
۵. `LLM_RUNTIME=ACTIVE` باید در آزمون واقعی با کلید تأیید شود؛ بدون آن قابلیت «مدل فعال» در دمو ادعا نشود.
۶. فیلم تقریباً پنج‌دقیقه‌ای باید از نسخه مستقر اجرا و ذخیره شود. بدون آن اثر از داوری حذف می‌شود.

**Stop-ship:** نشت secret، معرفی نام/شماره ساختگی به‌عنوان فروشنده واقعی، نقض سقف بودجه/شرط اعتباری، نشان دادن قیمت snapshot به‌عنوان قیمت زنده، خطای بدون بازیابی در مسیر خرید یا عدم دسترسی URL عمومی.
