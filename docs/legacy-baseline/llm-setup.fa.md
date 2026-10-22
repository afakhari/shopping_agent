# فعال‌سازی و عیب‌یابی مدل زبانی

## وضعیت فعلی مسیر خرید

در خروجی آزمون golden path، موارد زیر موفق بوده‌اند:

- readiness پایگاه داده
- جست‌وجوی واقعی کاتالوگ
- ایجاد مأموریت
- پاسخ SSE و رویدادهای مورد انتظار
- حفظ شرط‌های سخت و نمایش آفر واقعی

اما `intent_parser=heuristic` یعنی همین نوبت از مدل زبانی خروجی معتبر نگرفته است. `SMOKE_RESULT=PASS` به‌تنهایی به معنی فعال‌بودن LLM نیست؛ برای اثبات آن باید `LLM_RUNTIME=ACTIVE` و `llm_used=yes` دیده شود.

## تنظیم محلی provider

فایل `.env` باید کنار `compose.yaml` در ریشهٔ پروژه باشد. اگر وجود ندارد، از نمونه بساز:

```powershell
cd D:\projs\bazaar-compass
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
```

فقط داخل فایل محلی `.env` این متغیرها را با مقادیر واقعی provider خودت تنظیم کن:

```dotenv
LLM_ENABLED=1
LLM_PROVIDER=openai
LLM_API_KEY=کلید-واقعی-خودت
LLM_MODEL=gpt-6-luna
LLM_BASE_URL=https://api.openai.com/v1
LLM_TIMEOUT_SECONDS=10
```

- این نمونه مخصوص حسابی است که به OpenAI API دسترسی دارد. `gpt-6-luna` یک شناسهٔ رسمی API و گزینهٔ مقرون‌به‌صرفه برای کارهای پرتعداد و محدود است؛ در صورت نداشتن دسترسی، مدل را دقیقاً مطابق فهرست مدل‌های حساب خود انتخاب کن.
- اگر از provider سازگار با OpenAI استفاده می‌کنی، `LLM_PROVIDER=openai_compatible`، `LLM_BASE_URL` و `LLM_MODEL` را مطابق مستندات همان provider تنظیم کن.
- هرگز کلید API را در گفتگو، کد فرانت‌اند، فایل قابل commit یا لاگ قرار نده. `.env` در `.gitignore` است؛ پیش از commit وضعیت آن را بررسی کن.

## اعمال متغیرها در Docker

پس از تغییر `.env`، کانتینر بک‌اند را بازسازی و مجدداً ایجاد کن تا کد تشخیصی جدید و متغیرهای محیطی اعمال شوند:

```powershell
docker compose build backend
if ($LASTEXITCODE -ne 0) { throw "Backend build failed" }
docker compose up -d --force-recreate backend
docker compose ps
```

برای دیدن تشخیص ایمن، بدون چاپ کلید:

```powershell
Invoke-RestMethod http://localhost:8080/api/v1/health/ready/ | ConvertTo-Json -Depth 5
```

در `llm` فقط وضعیت و بولین‌های امن چاپ می‌شوند. `status` باید `configured` و `agent_mode` باید `model_configured` باشد. این فقط صحت ساختاری تنظیمات را اثبات می‌کند، نه دسترسی شبکه یا پذیرش درخواست توسط provider.

## آزمون واقعی مدل

اسکریپت golden path را به کانتینر بک‌اند کپی کن و این بار استفادهٔ واقعی از LLM را اجباری کن:

```powershell
docker cp .\scripts\smoke-golden-path.py bazaar-compass-backend-1:/tmp/smoke-golden-path.py
docker compose exec backend python /tmp/smoke-golden-path.py --base-url http://frontend --skip-contact --require-llm
```

خروجی مورد انتظار:

```text
intent_parser=llm
LLM_RUNTIME=ACTIVE
SMOKE_RESULT=PASS
llm_used=yes
```

اگر `FALLBACK_UNCONFIGURED` دیدی، یکی از تنظیمات لازم خالی/نامعتبر است؛ پاسخ سلامت، علت را مشخص می‌کند. اگر `FALLBACK_AFTER_CONFIG` دیدی، تنظیمات حاضرند ولی provider پاسخ قابل‌استفاده نداده است. علت دقیق (مانند HTTP 401/403/404/429، timeout یا پاسخ JSON نامعتبر) در لاگ بک‌اند ثبت می‌شود؛ کلید یا متن کامل پاسخ provider هرگز نباید به اشتراک گذاشته شود.

برای دیدن لاگ‌های مرتبط بدون چاپ فایل `.env`:

```powershell
docker compose logs --since 15m backend | Select-String -Pattern "LLM intent extraction"
```

## امنیت و نقش LLM

مدل فقط عبارت جست‌وجو، سقف بودجهٔ گفته‌شده، قصد خرید اعتباری و ترجیح ترتیب نتایج را استخراج می‌کند. قیمت، موجودی، آفر و فروشگاه از دیتابیس/قواعد بک‌اند می‌آیند؛ خروجی مدل اعتبارسنجی می‌شود و مدل نمی‌تواند شروط خرید را تضعیف کند. اگر provider در دسترس نباشد، fallback قطعی باید اجازه دهد تجربه از کار نیفتد؛ برای دمو با ادعای «هوش مصنوعی فعال»، اجرا باید با `--require-llm` موفق شود.
