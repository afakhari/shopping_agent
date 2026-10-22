# انتقال کد موجود به مخزن `afakhari/shopping_agent`

مخزن GitHub حاوی سند توسعه و Issueهای اجرایی است. این بسته شامل کد پایه محلی و مستندات قدیمی پروژه است که هنوز روی GitHub منتقل نشده‌اند. هیچ کلید API، فایل `.env` یا دیتاست خامی نباید از این بسته منتشر شود.

از ریشه پوشه استخراج‌شده اجرا کنید:

```bash
python scripts/import_to_shopping_agent.py
```

این دستور بدون ارتباط شبکه‌ای، فایل‌های مجاز را بازبینی و تعدادشان را گزارش می‌کند. برای ساخت شاخه و ارسال به GitHub، پس از نصب و احراز هویت Git، اجرا کنید:

```bash
python scripts/import_to_shopping_agent.py --push
```

اسکریپت، ریپوی GitHub را clone می‌کند، شاخه `bootstrap/import-existing-code` می‌سازد، کد موجود را انتقال می‌دهد، اسناد قدیمی را در `docs/legacy-baseline/` نگه می‌دارد و پس از بررسی‌های مقدماتی، branch را push می‌کند. **شاخه `main` بازنویسی یا force-push نمی‌شود.** سپس از لینک چاپ‌شده Pull Request بسازید و وضعیت CI و احتمال وجود اسرار را بازبینی کنید.

> اگر این شاخه از قبل ایجاد شده باشد، اجرای مجدد عمداً متوقف می‌شود تا به محتوای قبلی آسیب نزند. اجرای script فقط یک مسیر انتقال است؛ موفقیت اجرای برنامه و تست‌های runtime را اثبات نمی‌کند.

## Windows verification (2026-10-22)

Use Python 3.13: `py -3.13 scripts/import_to_shopping_agent.py --push`.
The content in this release was normalized to UTF-8/LF and checked using `git diff --cached --check` in a local test Git repo. No online push has been tested in this environment.
