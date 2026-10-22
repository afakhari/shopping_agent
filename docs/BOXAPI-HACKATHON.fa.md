# اتصال اعتبار هکاتون Starcoach به BoxAPI

## هدف
استفاده از اعتبار ۳ دلاری اختصاص‌داده‌شده در اطلاعیه هکاتون برای اتصال زبان طبیعی به بک‌اند Django.
مبنای رسمی: https://boxapi.ir/docs/ai/ و داده اعلام‌شده در اطلاعیه هکاتون.

**مهم:** مقدار `LLM_PROVIDER=boxapi` مخصوص آداپتر امن همین پروژه است و نام یک SDK جداگانه نیست.
این حالت فقط `model` و `messages` را به `https://ai.boxapi.ir/ai/v1/chat/completions` می‌فرستد، زیرا پارامترهای دیگر (temperature / response_format / max_tokens) برای همه مدل‌های BoxAPI در اطلاعیه ضمانت نشده‌اند.

## ۱. کارهایی که فقط صاحب حساب می‌تواند انجام دهد
1. در اطلاعیه رسمی هکاتون روی «فعال‌سازی اعتبار و دریافت API Key» کلیک کند.
2. URL و HTTPS پنل BoxAPI را بررسی کرده، رمز عبور را فقط در همان سایت وارد کند؛ نه در مخزن، نه در چت و نه در ابزار توسعه.
3. ۳ دلار را در کیف پول/حساب بررسی کند و تاریخ انقضا یا محدودیت اعتبار را در پنل بخواند.
4. کلید را از «مشاهده API Key» بردارد و در فایل خصوصی `.env` ریشه پروژه قرار دهد.
5. تا حد امکان گزینه شارژ خودکار را غیرفعال و مصرف اعتبار را پس از تست کنترل کند.

## ۲. اعمال در ویندوز و Docker
در PowerShell، در فولدر پروژه:

```powershell
git pull --ff-only origin main
notepad .env
```

اگر `.env` قبلاً وجود دارد، **متغیرهای PostgreSQL، DJANGO_SECRET_KEY و سایر تنظیمات آن را پاک نکن**. خط‌های زیر را اضافه/به‌روزرسانی کن. تنها جایگزینی لازم مقدار کلید خصوصی است:

```dotenv
LLM_ENABLED=1
LLM_PROVIDER=boxapi
LLM_API_KEY=PASTE_KEY_LOCALLY_NOT_IN_GITHUB
LLM_MODEL=gpt-5.4-mini
LLM_BASE_URL=https://ai.boxapi.ir/ai/v1
LLM_TIMEOUT_SECONDS=15
```

اگر فایل `.env` در ویرایشگر وجود نداشت، آن را با نام دقیق `.env` در همان پوشه `compose.yaml` بساز؛ از ذخیره با پسوند `.txt` اجتناب کن.
کلید `LLM_API_KEY` بدون کوتیشن و بدون فاصله اضافی نگهداری شود.

```powershell
docker compose up -d --build backend frontend
docker compose ps
Invoke-RestMethod http://localhost:8080/api/v1/health/ready/ | ConvertTo-Json -Depth 4
```

در جواب health، `llm.status` باید `configured` باشد. **این فقط پیکربندی را ثابت می‌کند.**

## ۳. تنها یک تماس واقعی آزمایشی
اسکریپت فعلی بدون SDK جدید و بدون چاپ کلید، همان API پروژه را آزمایش می‌کند:

```powershell
docker compose cp .\scripts\smoke-golden-path.py backend:/tmp/smoke-golden-path.py
docker compose exec -T backend python /tmp/smoke-golden-path.py --base-url http://frontend --skip-contact --require-llm
```

خروجی هدف: `LLM_RUNTIME=ACTIVE`، `llm_used=yes` و `SMOKE_RESULT=PASS`.
این تست یک پیام مأموریت با مدل واقعی اجرا می‌کند و استعلام نمایشی فروشنده را رد می‌کند.
اگر `FALLBACK_AFTER_CONFIG` مشاهده شد، مدل پاسخ معتبر JSON نداده یا درخواست شکست خورده است؛ فقط **کد وضعیت HTTP** را در `docker compose logs --tail 50 backend` بررسی کن، نه کلید و متن کامل لاگ را.

## ۴. عیب‌یابی
- `llm.status=missing_api_key`: فایل `.env` یا `LLM_API_KEY` درست تنظیم نشده؛ بعد از اصلاح backend را recreate کن.
- `invalid_base_url`: برای provider=boxapi نشانی دقیق HTTPS `https://ai.boxapi.ir/ai/v1` لازم است؛ `/chat/completions` را در Base URL تکرار نکن.
- `HTTP 401/403`: کلید نادرست، مجوز هکاتون یا اعتبار حساب را در پنل بررسی کن؛ خود کلید را ارسال نکن.
- `HTTP 400`: نام مدل یا قرارداد درخواست مشکل دارد؛ تنها خطای وضعیت در لاگ ثبت می‌شود. نسخه BoxAPI این پروژه پارامترهای غیرمستند Chat Completions را حذف می‌کند.
- `HTTP 429`: محدودیت نرخ یا اعتبار؛ تست پیاپی نفرست و پنل اعتبار را ببین.
- `TimeoutError`: مدل کند است یا دسترسی شبکه سرور با مشکل روبه‌روست؛ ابتدا timeout=15 را بررسی کن. آداپتر سقف ۲۰ ثانیه دارد تا سرور بیش از حد منتظر نماند.
- `llm.status=configured` ولی `FALLBACK_AFTER_CONFIG`: پاسخ model نامعتبر بوده یا خطای تماس وجود داشته است. بدون بررسی لاگ و آزمون کنترل‌شده آن را موفق اعلام نکن.
- مدل `gpt-6-luna` از فهرست مجاز است، اما بهتر است پس از تست با `gpt-5.4-mini` و بررسی هزینه در پنل امتحان شود.

## ۵. کنترل هزینه، امنیت و محدوده کار
- اعتبار ۳ دلاری هدیه طبق اطلاعیه است، نه وعده اعتبار نامحدود یا تأیید تراز کیف پول این حساب.
- **هیچ درخواست BoxAPI در CI اجرا نمی‌شود.** آزمون واحد از mock استفاده می‌کند.
- فقط درخواست‌هایی که واقعاً به تفسیر زبان طبیعی نیاز دارند به مدل ارجاع داده شوند؛ جست‌وجو، قیمت، اعتبار و فاصله با دیتابیس محاسبه می‌شوند.
- کلید صرفاً روی backend ذخیره شود. فایل `.env` را در GitHub commit نکن، `docker compose config` را بدون حذف secrets در جایی منتشر نکن.
- اتصال موفق LLM به‌معنای خرید کامل یا تماس واقعی فروشندگان نیست. دیتاست مسابقه برای برخی فروشندگان/شماره‌ها ساختگی است.
- در استقرار عمومی، متغیرها را در secret manager سرور تنظیم کن، نه داخل image یا فایل frontend.
