# وضعیت تحویل و محدودیت‌های تأییدشده | 2026-10-22

## منتشر و ادغام شد
- مخزن [shopping_agent](https://github.com/afakhari/shopping_agent) روی شاخه main دارای کد واقعی React/TypeScript/Vite و Django/DRF، Docker، تست‌های پایه و اسناد فنی است.
- [PR #9](https://github.com/afakhari/shopping_agent/pull/9) با روش squash در commit `4ba284eff35963fc1106dfe1e32151f0562c6863` ادغام شد.
- پس از اصلاح آدرس اسناد منتقل‌شده و تست SSE، کیفیت CI شاخه ورودی موفق شد: [quality-gates](https://github.com/afakhari/shopping_agent/actions/runs/39785054519).
- مراحل موفق: npm ci، typecheck، lint، frontend tests، build، کامپایل Python، بررسی scaffold، Django pytest و Ruff روی PostgreSQL مخصوص CI.
- قراردادهای JSON Schema نسخه ۱، README، UX، PRD، ایجنت، API و نقشه راه به همراه [۸ Issue اجرایی](https://github.com/afakhari/shopping_agent/issues) ثبت شده‌اند.
- بررسی مقدماتی بسته انتقال برای وجود فایل .env و الگوهای متداول کلیدهای خصوصی/توکن، مورد قطعی پیدا نکرد. این بررسی جایگزین اسکن امنیتی تخصصی نیست.

## هنوز تأیید نشده
- استقرار برنامه روی سرور عمومی و health/readiness با دیتاست واقعی.
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
