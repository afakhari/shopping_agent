# رفع کندی جست‌وجوی هدفون در دیتاست اصلی | ۲۳ اکتبر ۲۰۲۶

## شواهد از لاگ محلی
- تست واقعی `extract_intent` خروجی `BOXAPI_OK` داشت و مصرف/اتصال LLM از نظر parser تأیید شد.
- دستور `verify_dataset` تمام ۲۲۵٬۹۰۳ محصول / ۶٬۴۷۶ فروشگاه / ۳۳۱٬۵۰۶ آفر را تأیید کرد.
- PowerShell جست‌وجوی `/api/v1/catalog/search/?q=هدفون&page_size=1` را پس از حدود ۲۶ ثانیه timeout کرد؛ لاگ Gunicorn همان درخواست را با HTTP 200 ثبت کرد.
- این شواهد نشان‌دهنده تأخیر زیاد در مسیر جست‌وجو هستند؛ به‌تنهایی اثبات نمی‌کنند کدام عملگر SQL عامل آن بوده است.

## اصلاحات این شاخه
۱. انتخاب محصولات دارای آفر مجاز با `Exists` (semi-join) به‌جای join + `DISTINCT`، بدون تغییر شرط سخت بودجه/اعتبار/مکان و بدون تکراری شدن محصولات.
۲. چهار ایندکس GIN trigram روی `UPPER(normalized_title/category_name/brand_name/model)`. Django در PostgreSQL برای `icontains` از `UPPER(...)` استفاده می‌کند؛ ایندکس خام قبلی `product_title_trgm_idx` در migration 0002 الزاماً قابل استفاده برای این عبارت نیست. ساخت ایندکس به‌شکل `CONCURRENTLY`، اختیاری و صرفاً PostgreSQL است.
۳. فرمان پروفایل `profile_catalog_search` برای زمان‌سنجی مراحل matching/count/page و نمایش نام ایندکس‌های موجود و خلاصه پلن، بدون ارسال API هوش مصنوعی و بدون استخراج دیتاست.

مرجع: https://www.postgresql.org/docs/current/pgtrgm.html

## آزمون واقعی لازم (بدون PR و CI جدید)
از کامپیوتر ویندوز، در شاخه `perf/catalog-search-exists-trigram-profile`، کد بک‌اند را build کن. Volume PostgreSQL را پاک نکن و دیتاست را مجدداً import نکن.

```powershell
git fetch origin perf/catalog-search-exists-trigram-profile
git switch perf/catalog-search-exists-trigram-profile
docker compose up -d --build backend
docker compose exec -T backend python manage.py profile_catalog_search
```

**توجه:** migration اختیاری 0005 می‌تواند برای ایجاد ایندکس‌های بزرگ هنگام شروع کانتینر زمان مصرف کند. بعد از healthy شدن backend دستور پروفایل اجرا شود؛ retry مکرر همزمان ایندکس‌سازی نکن.

بعد با حداکثر ۲۵ ثانیه مهلت:
```powershell
$url = "http://localhost:8080/api/v1/catalog/search/?q=%D9%87%D8%AF%D9%81%D9%88%D9%86&page_size=1"
Measure-Command { Invoke-RestMethod -Uri $url -TimeoutSec 25 | Out-Null }
```

قبولی عملکرد وقتی ثبت می‌شود که benchmark واقعاً روی همین دیتاست، قبل/بعد مقایسه شود. هدف اولیه برای یک پرس‌وجوی عمومی حداقل حذف timeout و ترجیحاً p95 زیر ۳ ثانیه در محیط محلی است؛ این هدف هنوز اندازه‌گیری نشده است.

## رفع مشکل
- اگر migration ایندکس‌ها را skip کرد، خروجی `profile_catalog_search` نشان می‌دهد کدام ایندکس ایجاد نشده؛ دسترسی `pg_trgm` را کنترل کن.
- اگر `text_candidate_count` کند باشد، متن و index/plan تحلیل شود.
- اگر `eligible_product_count` کند باشد، Query Planner روی semi-join و index های offer بررسی شود.
- اگر فقط `full_search_page_size_1` کند باشد، correlated best_offer و sort/pagination باید در گام بعد بهینه شود.
- اگر همه مراحل سریع بودند ولی HTTP کند بود، proxy/Gunicorn/connection pool بررسی شوند.

**چیزی پاک یا reset نمی‌شود.** در صورت عدم بهبود، از PR/merge خودداری می‌کنیم و بر اساس `query_plan_nodes` اصلاح بعدی را انجام می‌دهیم.
