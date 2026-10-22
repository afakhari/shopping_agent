# راهنمای انتقال در ویندوز پس از خطای ^M

علت خطا در نسخه قبل: استفاده از `git -c core.autocrlf=false add -A` فایل‌های موجود در شاخه اصلی GitHub را دوباره با CRLF stage می‌کرد. نسخه اصلاح‌شده فقط ۱۶۴ فایل جدید را stage می‌کند، از `core.autocrlf=input` استفاده می‌کند و فایل‌های موجود در مخزن را دست‌نخورده نگه می‌دارد.

در پوشه استخراج‌شده دستور زیر را اجرا کنید:

```cmd
py -3.13 scripts/import_to_shopping_agent.py --push
```

پس از خروجی `Branch pushed`، شاخه را از لینک https://github.com/afakhari/shopping_agent/compare/main...bootstrap/import-existing-code?expand=1 بررسی کنید و Pull Request بسازید.

اگر Git هویت نویسنده را نداشت، فقط روی رایانه خودتان `git config --global user.name "Your Name"` و `git config --global user.email "your-address@example.com"` را با اطلاعات واقعی خود اجرا کنید.

این انتقال فقط کد موجود را در یک شاخه جدید قرار می‌دهد؛ موفقیت CI برنامه و اجرای پروژه را تضمین نمی‌کند.
