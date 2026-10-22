# آزمون مسیر طلایی Bazaar Compass

این آزمون به سرویس محلی در حال اجرا متصل می‌شود و از HTTP واقعی برای readiness، جست‌وجوی کاتالوگ، ایجاد مأموریت، ارسال turn با SSE، اعتبارسنجی شروط سخت و (به‌صورت پیش‌فرض) شبیه‌سازی استعلام استفاده می‌کند.

## پیش‌نیاز

- اجرای `docker compose up -d` از ریشه پروژه
- ورود داده‌ها در PostgreSQL
- درگاه پیش‌فرض `http://localhost:8080` در دسترس باشد
- Python استاندارد 3.10+؛ اسکریپت به بستهٔ خارجی وابسته نیست

## تست‌های کمکی بدون اتصال به سرویس

```powershell
python .\scripts\test_golden_path_smoke.py
```

این چهار تست، استخراج نتایج از Generative UI تو‌در‌تو و ردکردن نقض بودجه/اعتبار حضوری را بدون وابستگی خارجی می‌سنجند.

## اجرای آزمون کامل

از PowerShell در ریشه پروژه:

```powershell
python .\scripts\smoke-golden-path.py
```

به‌طور پیش‌فرض عبارت `فشارسنج` برای آزمون واقعی ابهام پزشکی/صنعتی استفاده می‌شود. اسکریپت یک مأموریت جدید و یک استعلام **شبیه‌سازی‌شده** ثبت می‌کند. هیچ تماس تلفنی یا ارتباط واقعی با فروشنده انجام نمی‌شود.

برای تست محصول مشخص دیگر:

```powershell
python .\scripts\smoke-golden-path.py --query "هدفون بی سیم"
```

برای آزمون سقف بودجه و حفظ آن در نتایج:

```powershell
python .\scripts\smoke-golden-path.py --query "هدفون بی سیم تا سقف ۳ میلیون تومان" --max-price-toman 3000000
```

برای اعمال شرط سخت خرید اعتباری حضوری (این آزمون ممکن است به‌درستی صفر نتیجه بدهد، اگر آفر واجد شرایطی برای عبارت پیدا نشود):

```powershell
python .\scripts\smoke-golden-path.py --query "هدفون" --in-person-credit --skip-contact
```

فقط آزمون readiness و مسیر گفتگو/جست‌وجو، بدون ثبت استعلام:

```powershell
python .\scripts\smoke-golden-path.py --skip-contact
```

## تأیید اتصال واقعی مدل زبانی

این اسکریپت پارامتر `intent_parser` را از رویداد `turn.completed` می‌خواند. `LLM_RUNTIME=ACTIVE` فقط وقتی چاپ می‌شود که همین درخواست از adapter مدل خروجی معتبر دریافت کرده باشد؛ اینکه `agent_mode=model_configured` از health برگردد به‌تنهایی اثبات پاسخ‌گویی provider نیست.

برای شکست دادن آزمون اگر مدل واقعی مصرف نشد:

```powershell
python .\scripts\smoke-golden-path.py --require-llm
```

نتایج ممکن:

- `LLM_RUNTIME=ACTIVE`: مدل این turn را پردازش کرده است.
- `LLM_RUNTIME=FALLBACK`: `LLM_API_KEY` یا `LLM_MODEL` تنظیم نیست، یا adapter فعال نشده است.
- `LLM_RUNTIME=NOT_USED`: پیکربندی ظاهراً وجود دارد اما درخواست به parser قطعی برگشته؛ لاگ backend را بررسی کن. خروجی model/API key هرگز چاپ نمی‌شود.

تنظیمات محلی باید در `.env` ریشه پروژه قرار گیرند و کلید فقط در بک‌اند بماند:

```dotenv
LLM_ENABLED=1
LLM_PROVIDER=openai_compatible
LLM_API_KEY=کلید_واقعی_را_محلی_قرار_بده
LLM_MODEL=نام_مدل_در_دسترسی_حساب
LLM_BASE_URL=https://api.openai.com/v1
LLM_TIMEOUT_SECONDS=6
```

بعد از تغییر `.env`، بک‌اند را بازسازی/راه‌اندازی مجدد کن:

```powershell
docker compose up -d --force-recreate backend
```

هرگز مقدار `LLM_API_KEY` را در گفتگو، اسکرین‌شات، log یا repo ارسال و commit نکن.

## معیار موفقیت

- `/api/v1/health/ready/` آماده است.
- API کاتالوگ HTTP 200 می‌دهد.
- ایجاد mission HTTP 201 می‌دهد.
- `turns/` با `Content-Type: text/event-stream` و HTTP 200 پاسخ می‌دهد.
- رویدادهای `user.message`, `assistant.message`, `ui.component`, `turn.completed` وجود دارند و sequence صعودی است.
- نتیجهٔ محصول دارای آفر و فروشگاه مشخص است و سقف بودجه/خرید اعتباری (در صورت فعال بودن) نقض نمی‌شود.
- استعلام منبع `demo_simulation` دارد.
- اگر از `--require-llm` استفاده شده باشد، parser همان turn باید `llm` باشد.
