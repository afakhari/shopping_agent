# راهنمای اجرایی ورود دیتاست و API جست‌وجو

**وضعیت:** کد پیاده شده، اما اجرای Django/DB در محیط تولیدکننده این تغییر به‌دلیل نبود dependencyها و Docker قابل تأیید نبود. پیش از دمو، تمام فرمان‌های بخش «اعتبارسنجی» باید در محیط واقعی اجرا شوند.

## 1. فایل‌های موردنیاز

ZIP داده باید شامل سه CSV باشد (نام دقیق فایل‌ها اهمیت دارد):

- `products.csv`
- `shops.csv`
- `offers.csv`

Importer ZIP را مستقیماً به‌صورت streaming می‌خواند؛ لازم نیست کل داده ۲۸۵MB استخراج و در RAM نگهداری شود. داده خام را وارد Git نکنید.

## 2. اجرای محلی

از ریشه پروژه:

```bash
# پوشه محلی خارج از Git
mkdir -p data
# فایل ZIP اصلی را به data/starcoach-dataset-v16-cap300-csv.zip کپی کنید

cd backend
python -m pip install -r requirements-dev.txt
python manage.py check
python manage.py migrate

# ابتدا فقط گزارش اعتبارسنجی؛ هیچ رکوردی نوشته نمی‌شود
python manage.py import_dataset --archive ../data/starcoach-dataset-v16-cap300-csv.zip --dry-run

# ورود واقعی پس از بررسی گزارش dry-run
python manage.py import_dataset --archive ../data/starcoach-dataset-v16-cap300-csv.zip
```

اگر CSVها قبلاً استخراج شده‌اند:

```bash
python manage.py import_dataset --input-dir ../data/raw --dry-run
python manage.py import_dataset --input-dir ../data/raw
```

در Docker Compose، کل پوشه `./data` به‌صورت read-only در `/app/data` mount می‌شود. پس از آماده‌شدن سرویس‌ها:

```bash
docker compose exec backend python manage.py migrate --noinput
docker compose exec backend python manage.py import_dataset --archive /app/data/starcoach-dataset-v16-cap300-csv.zip --dry-run
docker compose exec backend python manage.py import_dataset --archive /app/data/starcoach-dataset-v16-cap300-csv.zip
```

حساب اپ در کانتینر باید مجوز نوشتن در DB را داشته باشد؛ mount داده فقط خواندنی است.

## 3. رفتار importer

- CSV با `csv.DictReader` و UTF-8-SIG خوانده می‌شود؛ استفاده از split ساده روی کاما ممنوع است.
- مقادیر خالی و رشته literal `null` به `None` یا default نوع‌دار تبدیل می‌شوند.
- JSONهای تو‌در‌تو parse و نوع‌شان بررسی می‌شود. مقدار خراب گزارش می‌شود و با default امن جایگزین می‌شود؛ با `--strict-json` کل import پیش از نوشتن متوقف می‌شود.
- تکرار شناسه یا شناسه خالی، import را در preflight متوقف می‌کند.
- آفرهای یتیم در preflight شناسایی می‌شوند. فقط با `--allow-orphans` مجاز به ردکردن آن‌ها هستید.
- `--dry-run` جدول‌ها را تغییر نمی‌دهد؛ شمارش ردیف‌ها، شناسه‌های یکتا، JSON نامعتبر، قیمت/زمان نامعتبر، قیمت نامثبت، قیمت پرت، مختصات نامعتبر و آفر یتیم را گزارش می‌کند.
- برای هر اجرا، گزارش JSON و Markdown در `DATASET_REPORT_DIR` (پیش‌فرض ریشه `reports/`) نوشته می‌شود. در Docker مسیر آن `/app/reports` و volume جداگانه writable است. وضعیت `dry_run_complete`, `preflight_failed`, `import_complete` یا `import_failed_partial_batches_possible` در گزارش ثبت می‌شود.
- اجرای مجدد idempotent است: رکورد با همان source ID به‌روزرسانی می‌شود، نه اینکه دوباره ساخته شود.
- اگر import وسط batchها شکست بخورد، گزارش وضعیت partial را ثبت می‌کند؛ batchهای قبلی commit شده‌اند، پس پس از رفع علت، اجرای مجدد امن است.
- واردسازی به batchهای مستقل transactional تقسیم شده است؛ اگر یک batch بعدی fail شود، اجرای مجدد ادامه را امن می‌کند.
- قیمت خام حتی اگر پرت باشد نگهداری می‌شود؛ policy جست‌وجو قیمت‌های صفر، منفی و بالاتر از `MAX_REASONABLE_PRICE_TOMAN` را از رتبه‌بندی خرید حذف می‌کند.

## 4. API کاتالوگ

### `GET /api/v1/catalog/search/`

پارامترها:

| پارامتر | معنا |
|---|---|
| `q` | ضروری؛ عبارت فارسی/لاتین، ۱ تا ۲۰۰ کاراکتر |
| `max_price_toman` | سقف قیمت صحیح به تومان؛ ارقام فارسی یا لاتین پذیرفته می‌شوند |
| `must_have_in_person_credit` | `true` یعنی فروشگاه باید یک `payment_options` معتبر با `channel=in_person` داشته باشد |
| `lat`, `lon` | مبدأ اختیاری؛ هر دو با هم لازم‌اند |
| `radius_m` | شعاع ۱۰۰ تا ۱۰۰٬۰۰۰ متر؛ نیازمند مبدأ |
| `sort` | `relevance`, `price_asc`, `distance_asc`, `recent_price_change` |
| `page` | از ۱ به بالا؛ پیش‌فرض ۱ |
| `page_size` | پیش‌فرض ۲۰؛ بیشینه ۵۰ |

نمونه:

```http
GET /api/v1/catalog/search/?q=%D9%87%D8%AF%D9%81%D9%88%D9%86&max_price_toman=30000000&sort=price_asc&page=1&page_size=20
```

`total` تعداد محصولات یکتا پس از اعمال شروط سخت است، نه تعداد آفرها. هر نتیجه `best_offer` و `eligible_offers_count` دارد. قیمت در پاسخ به صورت رشته عددی تومان است تا precision جاوااسکریپت آسیب نبیند.

### جزییات

- `GET /api/v1/products/{product_id}/`
- `GET /api/v1/products/{product_id}/offers/` (همان فیلترهای خرید و صفحه‌بندی)
- `GET /api/v1/shops/{shop_id}/`

### قواعد eligibility

1. دیتاست تمام فروشگاه‌های این نسخه را در تهران تعریف می‌کند؛ هر نتیجه کاتالوگ از Shop/Offer همین مجموعه می‌آید.
2. نتیجه اصلی باید دست‌کم یک آفر واجد شرایط داشته باشد؛ دسته‌بندی فروشگاه جایگزین آفر نیست.
3. اگر سقف بودجه تعیین شود، آفر با قیمت null واجد شرط نیست. بدون بودجه می‌توان آفر با قیمت نامشخص را نمایش داد، اما با برچسب `price_quality=unknown_price` یا `unknown_timestamp` بر اساس نوع فقدان اطلاعات.
4. وجود Offer اثبات موجودی امروز نیست؛ `last_price_changed_at` هم زمان تغییر قیمت است، نه زمان تأیید موجودی.
5. شرط اعتباری حضوری فقط `channel=in_person` را می‌پذیرد؛ `unknown` هرگز واجد شرایط قطعی نیست.
6. اگر مبدأ و شعاع تعیین شوند، فاصله با Haversine محاسبه و سپس شعاع دقیق اعمال می‌شود؛ ابتدا bounding box برای کاهش تعداد رکوردها استفاده می‌شود.
7. اگر نتیجه‌ای منطبق وجود ندارد، API آرایه خالی و `total=0` برمی‌گرداند؛ نتیجه نقض‌کننده شروط به کاربر نشان داده نمی‌شود.

## 5. اعتبارسنجی و عیب‌یابی

در محیط دارای dependencies:

```bash
cd backend
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate
pytest -q
ruff check .
ruff format --check .
```

Smoke test پس از ورود داده:

```bash
curl 'http://localhost:8000/api/v1/catalog/search/?q=%D9%87%D8%AF%D9%81%D9%88%D9%86&page_size=5'
curl 'http://localhost:8000/api/v1/catalog/search/?q=%D9%87%D8%AF%D9%81%D9%88%D9%86&must_have_in_person_credit=true&page_size=5'
```

اگر خطای `no such function: RADIANS` یا مشابه دریافت شد، SQLite آن runtime توابع ریاضی را ندارد؛ مسیر فاصله را روی PostgreSQL (محیط اصلی) تست کنید یا تابع Haversine قابل‌حمل ثبت‌شده برای SQLite اضافه کنید. برای آزمون CI بهتر است فیلترهای فاصله هم روی PostgreSQL واقعی تست شوند.
