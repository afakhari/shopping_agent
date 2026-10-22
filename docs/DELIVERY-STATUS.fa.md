# وضعیت تحویل و محدودیت‌های تأییدشده | 2026-10-22

## منتشر و ادغام شد
- مخزن [shopping_agent](https://github.com/afakhari/shopping_agent) روی شاخه main دارای کد واقعی React/TypeScript/Vite و Django/DRF، Docker، تست‌های پایه و اسناد فنی است.
- [PR #9](https://github.com/afakhari/shopping_agent/pull/9) با روش squash در commit `4ba284eff35963fc1106dfe1e32151f0562c6863` ادغام شد.
- پس از اصلاح آدرس اسناد منتقل‌شده و تست SSE، کیفیت CI شاخه ورودی موفق شد: [quality-gates](https://github.com/afakhari/shopping_agent/actions/runs/39785054519).
- مراحل موفق: npm ci، typecheck، lint، frontend tests، build، کامپایل Python، بررسی scaffold، Django pytest و Ruff روی PostgreSQL مخصوص CI.
- قراردادهای JSON Schema نسخه ۱، README، UX، PRD، ایجنت، API و نقشه راه به همراه [۸ Issue اجرایی](https://github.com/afakhari/shopping_agent/issues) ثبت شده‌اند.
- بررسی مقدماتی بسته انتقال برای وجود فایل .env و الگوهای متداول کلیدهای خصوصی/توکن، مورد قطعی پیدا نکرد. این بررسی جایگزین اسکن امنیتی تخصصی نیست.

## تأیید محیط محلی Windows/Docker با دیتاست واقعی (گزارش کاربر، ۲۲ اکتبر ۲۰۲۶)

- کاربر موفقیت اتصال Django به PostgreSQL 17 و اجرای migrations با خروجی `No migrations to apply` را گزارش کرد.
- فرمان `verify_dataset` در محیط Docker روی PostgreSQL **۲۲۵٬۹۰۳ محصول، ۶٬۴۷۶ فروشگاه و ۳۳۱٬۵۰۶ آفر** و شناسه‌های نمونه را تأیید کرد.
- پس از رفع ناسازگاری رمز Volume قدیمی با `.env` و اشکال UTF-8 در Windows PowerShell 5.1، اجرای `setup-dataset.ps1` با خروجی `Search smoke test passed: 1458 matching products.` موفق شد.
- هر سه سرویس Docker در زمان آزمایش healthy/running بودند و درگاه برنامه روی `http://localhost:8080` اعلام شد.
- import دوباره انجام نشد، چون دیتاست موجود و معتبر شناسایی شد؛ بنابراین **زمان اولین import واقعی** در این مرحله ثبت نشده است.
- این شواهد تأیید **راه‌اندازی محلی و جست‌وجوی پایه** هستند؛ تست‌های تعاملی مرورگر، سناریوهای کامل خرید، امنیت و استقرار عمومی هنوز نیاز به آزمون دارند.
- مطابق سیاست کاهش هزینه، GitHub Actions برای رفع اشکالات محلی و ثبت این گزارش اجرا نشده است.

## آزمون واقعی مسیر HTTP خرید با دیتاست کامل (گزارش Windows، ۲۲ اکتبر ۲۰۲۶)

- بعد از `git pull` تا commit `5d40c50` و اجرای `check-golden-path.ps1 -SkipBackendTests`، Docker هر سه سرویس را سالم گزارش کرد. Django check و `makemigrations --check --dry-run` نیز بدون خطا بودند.
- شمارش PostgreSQL و رابطه‌های نمونه مجدداً تأیید شد: **225903 محصول، 6476 فروشگاه، 331506 آفر**.
- **۹ تست مستقل ابزار golden path** (از جمله انتقال کوکی نشست بین JSON و SSE) در ۰٫۱۴۷ ثانیه موفق شدند. در اجرای قبلی، **۶۹ تست Django** نیز با نتیجه `OK` تمام شدند.
- **۶ مرحله HTTP واقعی از پشت پروکسی فرانت‌اند** موفق شد: health/readiness، کاتالوگ با **۱۴۵۸ نتیجه هدفون**، ایجاد مأموریت، دریافت **۵ رویداد SSE** با `runtime=langgraph`، اعتبارسنجی شروط خرید و استعلام شبیه‌سازی‌شده فروشنده.
- استعلام واقعی آزمایش برابر `no_answer` بود: **صفر آفر پشتیبان همان کالا** و **پنج محصول جایگزین** با شروط خرید پیشنهاد شدند. این نتیجه شواهد اجرای مسیر بازیابی اولیه است، نه تأیید ادامه کامل تا برنامه مراجعه.
- وضعیت ایجنت `deterministic_fallback` و `intent_parser=heuristic` بود؛ **LLM واقعی در این آزمایش غیرفعال** و هیچ تماس واقعی با فروشنده انجام نشده است.
- خروجی نهایی `SMOKE_RESULT=PASS` و `ALL REQUESTED LOCAL CHECKS PASSED` است؛ volume حذف یا دیتاست مجدد import نشد.
- سپس در commit `998a2d0` قابلیت **آزمون اختیاری `-FullJourney`** اضافه شد تا retry/idempotency، استعلام جایگزین، برنامه مراجعه و بازیابی snapshot هم از پشت HTTP بررسی شوند. اجرای این آزمون جدید روی سیستم کاربر **هنوز تأیید نشده** است.

## هنوز تأیید نشده
- استقرار برنامه روی سرور عمومی و سنجش health/readiness در محیط production. راه‌اندازی محلی داده‌دار تأیید شده است.
- عملکرد مدل زبانی و SDK نقشه با کلید واقعی و سهمیه مناسب.
- E2E مرورگر روی موبایل فارسی و معیارهای UX/دسترس‌پذیری.
- مأموریت LangGraph ماندگار با checkpoint تولیدی، استعلام چندمنظوره و بازیابی کامل شکست.
- دقیق‌بودن موتور جست‌وجو روی مجموعه golden query برچسب‌خورده.
- صدور ویدئوی دموی مسابقه.

## گام‌های بعدی
۱. [Issue #2](https://github.com/afakhari/shopping_agent/issues/2): dataset import با داده اصلی، readiness و build/deploy verification.
۲. [Issue #3](https://github.com/afakhari/shopping_agent/issues/3) و [#4](https://github.com/afakhari/shopping_agent/issues/4): UX و بازیابی جست‌وجوی فارسی.
۳. [Issue #5](https://github.com/afakhari/shopping_agent/issues/5) و [#6](https://github.com/afakhari/shopping_agent/issues/6): نقشه تهران و مأموریت ایجنت.
۴. [Issue #7](https://github.com/afakhari/shopping_agent/issues/7) و [#8](https://github.com/afakhari/shopping_agent/issues/8): برنامه مراجعه، تست واقعی، دیپلوی و ویدئوی دمو.

**معیار گزارش‌دهی:** سبزبودن CI پایه نشان می‌دهد کد موجود build و test می‌شود؛ به معنی اتمام محصول مسابقه یا readiness عملیاتی نیست.
