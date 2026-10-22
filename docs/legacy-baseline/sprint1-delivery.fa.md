# گزارش تحویل Sprint 1 — Import، Search و Offer Comparison

## هدف

تبدیل scaffold اولیه به یک هسته کاتالوگ قابل توسعه: ورود داده به‌شکل دسته‌ای، جست‌وجوی محصول با فیلتر قطعی، و مقایسه فروشگاه‌هایی که آفر واجد شرایط برای همان محصول دارند.

## تغییرات پیاده‌سازی‌شده

### داده و ورود دیتاست

- مدل‌های `Product`, `Shop`, `Offer` با `source_id` منبع به‌عنوان کلید اصلی.
- قیمت با `DecimalField` ذخیره می‌شود تا گردکردن float روی مبلغ اثر نگذارد.
- JSONهای منبع در `JSONField` حفظ می‌شوند.
- فلگ `Shop.accepts_in_person_credit` از `payment_options` مشتق می‌شود و ایندکس دارد؛ migration `0003` مقدار موجود را backfill می‌کند.
- فرمان `import_dataset` ورودی ZIP یا پوشه CSV را streaming می‌خواند، preflight و dry-run دارد، JSON و انواع مهم را کنترل می‌کند و upsertهای دسته‌ای انجام می‌دهد.
- اجرای مجدد importer با ID منبع idempotent است. اگر خطا بعد از commit چند batch رخ دهد، گزارش به‌طور صریح وضعیت احتمال partial batches را ثبت می‌کند.

### جست‌وجو و انتخاب پیشنهاد

- جست‌وجوی فارسی پس از نرمال‌سازی حروف عربی/فارسی، ارقام و فاصله انجام می‌شود.
- تنها محصولاتی وارد نتایج می‌شوند که حداقل یک آفر پس از اعمال شروط سخت داشته باشند.
- سقف بودجه، خرید اعتباری حضوری، شعاع و ترتیب قیمت/فاصله/تازگی در سرویس قطعی query اعمال می‌شوند.
- قیمت صفر، منفی و پرت وارد رتبه‌بندی خرید نمی‌شود؛ قیمت اصلی منبع برای ممیزی حفظ می‌شود.
- تاریخ قیمت و وضعیت `price_quality` از موجودی زنده مستقل هستند.
- endpoint مقایسه، آفرهای همان محصول را با همان شروط خرید برمی‌گرداند.

### رابط کاربر

- جست‌وجو با debounce و مدیریت لغو درخواست.
- فیلتر بودجه و اعتبار، ترتیب و صفحه‌بندی.
- کارت محصول با قیمت، تاریخ تغییر، وضعیت کیفیت قیمت و فروشگاه پیشنهادی.
- کاربر می‌تواند آفرهای همان محصول را باز کند و فروشگاه‌های واجد شرایط را کنار هم مقایسه کند.
- حالت خطا و حالت نتیجه خالی وجود دارند؛ شروط سخت خودکار تغییر نمی‌کنند.

## قرارداد API تحویل‌شده

- `GET /api/v1/catalog/search/`
- `GET /api/v1/products/{product_id}/`
- `GET /api/v1/products/{product_id}/offers/`
- `GET /api/v1/shops/{shop_id}/`

برای پارامترها و payloadهای دقیق، `api-contract.fa.md` و `import-and-search.fa.md` مرجع هستند.

## بررسی‌های این تحویل

**موفق و انجام‌شده:** Python compileall، بررسی ثابت ساختار پروژه، parse فایل‌های JSON/YAML، TypeScript syntax parse برای تمام TS/TSX، typecheck فایل API client با `tsc`، و بررسی طول خطوط Python.

**هنوز تأیید نشده:** Django migrations/checks، pytest، import واقعی به PostgreSQL، فرانت‌اند build و lint کامل، Docker build/up و deploy. در محیط ساخت Django و Docker وجود نداشتند و دسترسی به registryهای PyPI/npm به دلیل DNS برقرار نشد.

## فرمان‌های شروع تست در محیط واقعی

```bash
cd backend
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate
pytest -q
python manage.py import_dataset --archive ../data/starcoach-dataset-v16-cap300-csv.zip --dry-run
python manage.py import_dataset --archive ../data/starcoach-dataset-v16-cap300-csv.zip
```

پس از اجرای موفق import، فرانت‌اند را با endpoint واقعی API آزمایش کنید و سپس `npm ci`, lint, typecheck, test, build و smoke test Docker/Compose را اجرا کنید.

## خارج از محدوده این تحویل

- LangGraph mission workflow
- ذخیره mission و رویدادهای آن
- شبیه‌ساز تماس فروشنده
- جایگزین‌یابی بعد از no-answer/unavailable
- Generative UI registry و stream رویدادهای عامل
- نقشه واقعی و بهینه‌سازی چندتوقفی مسیر
- دیپلوی عملیاتی
