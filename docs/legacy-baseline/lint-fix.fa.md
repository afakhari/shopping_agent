# اصلاح lint گزارش‌شده در Windows

## وضعیت پیش از اصلاح

خروجی محلی کاربر نشان داد:

- Django system checks: موفق.
- `makemigrations --check --dry-run`: بدون تغییر.
- تست بک‌اند: 48 passed.
- Ruff: 9 finding شامل هفت مورد B033 برای عبارت‌های تکراری set، یک F401 و یک F405.

## اصلاحات

1. `backend/apps/agent/graph.py`: set مربوط به `STOP_WORDS` پاک‌سازی شد و ورودی‌های تکراری حذف شدند. گونه‌های یکتای رایج فارسی نگه داشته شده‌اند.
2. `backend/apps/missions/services.py`: import بلااستفاده `transaction` حذف شد.
3. `backend/config/settings/local.py`: ارجاع `SECRET_KEY` و `ALLOWED_HOSTS` با نام ماژول `base_settings` انجام می‌شود تا F405 حذف شود؛ import ستاره‌ای برای به ارث بردن باقی تنظیمات Django حفظ شده است.

## بررسی پس از اصلاح

در محیط بسته‌بندی، Python AST و اسکریپت بررسی ساختاری پروژه اجرا می‌شوند؛ Ruff در آن محیط نصب نیست. بنابراین رفع موارد گزارش‌شده بر اساس دقیقاً همان 9 خروجی انجام شده، اما نتیجه نهایی باید در محیط کاربر با این فرمان تأیید شود:

```powershell
Set-Location D:\projsazaar-compassackend
.\.venv\Scripts\python.exe -m ruff check .
```

در صورت موفقیت، به ریشه پروژه برگردید و اسکریپت کامل را دوباره اجرا کنید:

```powershell
Set-Location D:\projsazaar-compass
.\scriptserify-local.ps1
```
