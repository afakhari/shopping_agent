# وضعیت تحویل و محدودیت‌های تأییدشده | 2026-10-22

## انجام‌شده روی GitHub
- مخزن موجود و مجوز نوشتن تأیید شد؛ LICENSE اولیه حفظ شده است.
- سند نیازمندی، UX، معماری، مدل داده و جست‌وجو، ایجنت، API، کیفیت و نقشه راه روی شاخه main commit شده‌اند.
- قراردادهای JSON Schema نسخه ۱ برای رویداد مأموریت، پاسخ استعلام و برنامه مراجعه اضافه شده‌اند.
- هشت Issue با معیار پذیرش قابل‌ارزیابی ثبت شده است: https://github.com/afakhari/shopping_agent/issues
- Workflow با عنوان blueprint-sanity روی commit 26077508438c848f065790a3ffa15346a88552ab با success پایان یافت. این بررسی فقط وجود اسناد و صحت نحوی JSON Schema و تست‌های ساختاری را پوشش می‌دهد.

## هنوز انجام‌نشده
- انتقال تمام source code موجود در بسته محلی به GitHub. دلیل: اتصال GitHub تنها محتوای متنی را برای نوشتن مستقیم می‌پذیرد و شبکه container برای git push به github.com قابل دسترس نیست.
- اجرای واقعی برنامه Django/React، import دیتاست، frontend build، backend pytest، test مرورگر، تماس با provider خارجی و دیپلوی.
- ادغام شاخه import از طریق Pull Request.

## راه اقدام
۱. بسته BazaarCompass-Shopping-Agent-Import-Ready.zip موجود در گفتگو را دانلود و استخراج کنید.
۲. با Git احراز هویت کنید.
۳. در ریشه بسته، python scripts/import_to_shopping_agent.py --push اجرا کنید.
۴. از https://github.com/afakhari/shopping_agent/compare/main...bootstrap/import-existing-code?expand=1 یک Pull Request بسازید.
۵. پس از بررسی اسرار، CI و تست‌ها، merge کنید.

## معیار گزارش‌دهی
تا زمانی که CI برنامه و deployment smoke tests واقعاً اجرا نشده‌اند از عبارت «نسخه عملیاتی آماده مسابقه» استفاده نشود. تغییر در UI و بک‌اند باید evidence قابل‌مشاهده داشته باشد.
