# ورود دیتاست مسابقه به PostgreSQL محلی (Windows)

این فرایند روی کامپیوتر کاربر اجرا می‌شود و به GitHub Actions نیازی ندارد. ZIP خام را در GitHub عمومی منتشر نکنید.

## پیش‌نیاز
Docker Desktop روشن (WSL2)، Git و فایل starcoach-dataset-v16-cap300-csv.zip دانلودشده از Sources پروژه. اولین build نیاز به اینترنت برای imageها و وابستگی‌ها دارد. Python روی Windows برای این روش لازم نیست.

## دستور اجرای اولیه (PowerShell)

    git clone https://github.com/afakhari/shopping_agent.git
    cd shopping_agent
    powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-dataset.ps1 -ArchivePath "$env:USERPROFILE\Downloads\starcoach-dataset-v16-cap300-csv.zip"

اگر ZIP در Downloads نیست، مقدار ArchivePath را اصلاح کنید.

## ابزار چه می‌کند؟
1. SHA-256 آرشیو را با فایل ممیزی‌شده مقایسه می‌کند.
2. ZIP را به پوشه data منتقل می‌کند که در .gitignore است.
3. اگر فایل .env وجود نداشته باشد، تنظیمات خصوصی محلی با کلید و رمز تصادفی می‌سازد.
4. PostgreSQL و Django را اجرا می‌کند و migration اعمال می‌شود.
5. ابتدا وجود داده با تعداد دقیق و شناسه‌های نمونه را بررسی می‌کند؛ تکرار import را حذف می‌کند.
6. اگر داده وجود ندارد: dry-run و سپس import واقعی روی PostgreSQL.
7. شمارش 225903 محصول، 6476 فروشگاه و 331506 آفر و سه شناسه نمونه را کنترل می‌کند.
8. فرانت‌اند را بالا می‌آورد و روی عبارت «هدفون» درخواست واقعی به API می‌فرستد.

نتیجه قابل‌قبول: Dataset counts and sample relationships verified و Search smoke test passed.
نشانی برنامه: http://localhost:8080 (یا APP_PORT تنظیم‌شده).

## رفع خطای PostgreSQL در Volume قدیمی

اگر در لاگ backend عبارت `password authentication failed for user "bazaar_compass"` و در لاگ db عبارت `Skipping initialization` دیده شد، به این معنی است که رمز PostgreSQL در Volume قبلی مانده، اما فایل `.env` رمز جدیدی دارد. **دیتابیس خراب نیست و نباید Volume را پاک کنید.**

ابتدا تازه‌ترین اسکریپت را دریافت کنید:

```powershell
git pull --ff-only origin main
```

سپس برای **هماهنگ‌کردن رمز کاربر محلی با .env به‌صورت صریح** اجرا کنید:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-dataset.ps1 -ArchivePath "$HOME\Downloads\starcoach-dataset-v16-cap300-csv.zip" -RepairDbPassword
```

این عملیات فقط زمانی وارد مرحله تغییر رمز می‌شود که آزمون TCP با رمز فعلی شکست بخورد، اتصال ادمین از طریق سوکت محلی برقرار باشد، و نام دیتابیس/کاربر و شکل رمز با تنظیمات خودکار پروژه یکسان باشند. رمز از طریق stdin به PostgreSQL فرستاده می‌شود و در لاگ عمومی چاپ نمی‌شود. PostgreSQL Volume، جدول‌ها و رکوردها حفظ می‌شوند.

اگر این مسیر هم خطا داد، خروجی `docker compose ps` و `docker compose logs --tail 80 backend db` را بدون محتوای فایل `.env` گزارش کنید. **دستور `docker compose down -v` اجرا نکنید.** این روش مخصوص محیط توسعه محلی است و برای تغییر رمز PostgreSQL محیط production طراحی نشده است.

## بررسی و مدیریت

    docker compose exec -T backend python manage.py verify_dataset --products 225903 --shops 6476 --offers 331506
    docker compose logs --tail 100 backend db frontend
    docker compose down

برای import اجباری مجدد، اسکریپت setup-dataset.ps1 را با گزینه ForceReimport اجرا کنید.
هشدار: دستور docker compose down -v اطلاعات Volume دیتابیس را حذف می‌کند؛ بدون تصمیم آگاهانه اجرا نکنید.

## محدودیت اثبات
اجرای موفق این اسکریپت فقط ورود دیتاست محلی، تطبیق تعداد رکوردها و smoke test API را ثابت می‌کند. مرورگر موبایل، نقشه واقعی، LLM، کل سناریوی مأموریت و محیط production همچنان به تست مستقل نیاز دارند.
