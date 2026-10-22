# نقطه کنترل کیفیت مسیر خرید | ۲۲ اکتبر ۲۰۲۶

## قابلیت‌های پیاده‌شده
- نشست مالک مأموریت، دسترسی ایزوله به state و events و جلوگیری از استفاده از UUID به‌تنهایی.
- استعلام `client_request_id`، replay پاسخ بدون تماس تکراری، تراکنش و قفل مأموریت، migrationها و تست‌های رگرسیون.
- برنامه مراجعه ماندگار با شناسه محصول/فروشگاه/آفر، ساعات ثبت‌شده، موقعیت روی نقشه، فروشنده پشتیبانِ دارای آفر واجد شرایط و وضعیت «موجودی استعلام‌نشده».
- GET `/api/v1/missions/<uuid>/visit-plan/` برای صاحب نشست.
- مقایسه حداکثر سه محصول با مشخصات فنی مشترک واقعی؛ مقادیر مفقود «نامشخص».
- سناریوی شبیه‌سازی تغییر قیمت بدون اختراع مبلغ جدید.
- ابزار Windows `scripts/check-golden-path.ps1` برای بررسی Django، migration، شمارش دیتاست و مسیر HTTP مأموریت بدون GitHub Actions یا حذف داده.

## شواهد و محدودیت‌ها
کد در main ثبت شده است. کنترل کیفیت مجموعه در [GitHub Actions](https://github.com/afakhari/shopping_agent/actions/runs/39814104330) با نتیجه success تکمیل شد؛ ساختار فایل‌های commit ادغام‌شده با نسخه تست‌شده یکسان بود. ۶۹ تست Django و ۹ تست ابزار محلی قبلاً موفق شدند و آزمون `-FullJourney` نیز روی دیتاست واقعی با بازیابی فروشنده جایگزین، idempotency و برنامه مراجعه به `SMOKE_RESULT=PASS` رسید. این شواهد فقط مسیر محلی شبیه‌سازی‌شده را تأیید می‌کنند، نه انتشار عمومی یا تماس واقعی. پس از checkpoint، این‌ها باقی می‌مانند: محدودیت نرخ و امنیت production، نقشه و لیست یکپارچه، ETA معتبر و ساعت بازبودن، استعلام هدفمند قیمت/ساعات، LangGraph چندمرحله‌ای با checkpoint بومی، سنجش ۵۰ query و MRR/Recall، تست‌های E2E و accessibility، دیپلوی عمومی و ویدئوی مسابقه.

## دستور آزمون کامل محلی
```powershell
git pull --ff-only origin main
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check-golden-path.ps1 -SkipBackendTests -FullJourney
```

این دستور ZIP را دوباره وارد یا Docker volume را حذف نمی‌کند. فایل `.env` را منتشر نکنید.
