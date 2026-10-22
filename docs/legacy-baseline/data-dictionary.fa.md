# فرهنگ داده و قرارداد مدل‌ها

**منبع:** ZIP با نام `starcoach-dataset-v16-cap300-csv.zip`، نسخه cap300. فیلدها و معنا از README و نمونه‌های CSV بررسی شده‌اند. شمارش‌ها در `dataset-profile.fa.md` است.

## 1. قواعد عمومی CSV

- UTF-8 با header.
- آرایه‌ها و objectهای تو‌در‌تو به شکل JSON فشرده در سلول CSV ذخیره شده‌اند.
- مقدار گمشده غالباً رشته literal `null` است؛ بعضی ستون‌ها نیز سلول خالی دارند.
- CSV باید با parser استاندارد و quoting صحیح خوانده شود؛ استفاده از `split(',')` ممنوع است.
- JSON نامعتبر یا مقدار نامنتظره باید در گزارش import ثبت شود؛ import نباید بی‌سر و صدا داده را حذف کند.
- داده خام و نسخه آن immutable باقی بماند؛ هر اصلاح یا normalization باید در فیلد کمکی یا مرحله ingest انجام شود.

## 2. `products.csv`

کلید طبیعی منبع: `product_id`. تعداد ورودی: 225,903.

| ستون | نوع منبع | معنا | قاعده مدل |
|---|---|---|---|
| `product_id` | string | شناسه یکتا | اجباری، unique |
| `persian_title` | string/null | عنوان اصلی فارسی | نمایش اصلی؛ قبل از جست‌وجو normalize copy بساز |
| `brand_name` | string/null | برند | null را خالی نشان بده، نه عبارت `null` |
| `category_name` | string/null | دسته محصول | برای فیلتر و کمک رتبه‌بندی |
| `model` | string/null | مدل اختصاصی | در بسیاری رکوردها خالی است؛ فقط اگر موجود باشد استفاده کن |
| `specs` | JSON array | ویژگی‌های فنی | عنصرها معمولاً `{key, section, value}` هستند |
| `image_urls` | JSON array | URL تصاویر | ممکن است آرایه خالی باشد؛ تصاویر را validate و lazy-load کن |

### شکل `specs`

```json
[
  {"key":"وزن","section":"مشخصات کلی","value":"625 گرم"},
  {"key":"رنگ","section":"مشخصات کلی","value":"مشکی"}
]
```

`key`, `section`, `value` رشته‌اند، اما باید در parser نوع‌سنجی و ورودی ناقص تحمل شود. این ویژگی‌ها مقدارهای نمایشی‌اند؛ همه آنها عددی یا قابل مقایسه نیستند. برای مقایسه مشخصه‌ها، واحدها و معنا را حدس نزنید.

## 3. `shops.csv`

کلید طبیعی منبع: `shop_id`. تعداد ورودی: 6,476. مجموعه ارائه‌شده برای تهران است و ستون `city` مستقل ندارد.

| ستون | نوع منبع | معنا/نکته |
|---|---|---|
| `shop_id` | string | شناسه یکتا و کلید ارتباطی |
| `name` | string/null | نام نمایشی فروشگاه در دیتاست |
| `category_names` | JSON array | دسته‌هایی که فروشگاه در آنها ثبت شده؛ وجود دسته، وجود کالای خاص را اثبات نمی‌کند |
| `address` | string/null | نشانی متنی؛ ممکن است پاساژ/طبقه/واحد داشته باشد |
| `location_label` | string/null | برچسب محدوده مکانی، نه جایگزین مختصات |
| `lat` | numeric/null | عرض جغرافیایی |
| `lon` | numeric/null | طول جغرافیایی |
| `contacts` | JSON array | راه‌های ارتباطی |
| `payment_options` | JSON array | گزینه پرداخت اعتباری/سرویس‌های ثبت‌شده |
| `weekly_hours` | JSON object | برنامه روزهای هفته با status و shifts |
| `website_url` | string/null | آدرس وب‌سایت ثبت‌شده |
| `instagram` | string/null | حساب ثبت‌شده اینستاگرام |
| `supports_fast_delivery` | bool/null | سه حالت true، false، unknown/null؛ null را false فرض نکن |

### شکل `contacts`

```json
[{"channel":"phone","display_number":"۰۲۱۱۲۳۴۵۶۷۸"}]
```

در داده بررسی‌شده channel برابر `phone` است. رشته شماره برای نمایش حفظ شود؛ برای لینک تماس، تبدیل ارقام/استانداردسازی جداگانه و تست‌شده باشد. در نسخه داوری، درخواست تماس به simulator کنترل‌شده فرستاده می‌شود.

### شکل `payment_options`

```json
[
  {
    "provider_name":"ترب‌پی",
    "channel":"in_person",
    "category_names":[],
    "min_price_toman":null,
    "max_price_toman":null
  }
]
```

فیلدها: `provider_name`, `channel`, `category_names`, `min_price_toman`, `max_price_toman`. کانال‌های مشاهده‌شده `in_person` و `unknown` هستند. مقادیر حداقل/حداکثر ممکن است null باشند. واجد شرایط بودن «خرید اعتباری حضوری» فقط زمانی true است که دست‌کم یک option با `channel=in_person` از نظر ساختار درست باشد.

### شکل `weekly_hours`

کلیدهای روز هفته با نام انگلیسی کوتاه‌اند: `sat`, `sun`, `mon`, `tue`, `wed`, `thu`, `fri`. هر روز ممکن است شکل زیر داشته باشد:

```json
{
  "sat": {
    "status":"declared",
    "shifts":[{"start_time":"10:00:00","end_time":"19:00:00"}]
  }
}
```

statusهای مشاهده‌شده: `declared`, `closed`, `unsupported`. داده خالی `{}` نیز وجود دارد. زمان‌ها به شکل `HH:MM:SS` هستند؛ شیفت‌هایی که از نیمه‌شب عبور می‌کنند یا start و end برابر دارند باید با قاعده صریح بررسی شوند. هرگز status=`unsupported` یا روز گمشده را به معنی بازبودن فرض نکنید. timezone نمایش: `Asia/Tehran`.

## 4. `offers.csv`

کلید طبیعی منبع: `offer_id`. تعداد ورودی: 331,506.

| ستون | نوع منبع | معنا/نکته |
|---|---|---|
| `offer_id` | string | شناسه آفر؛ unique |
| `product_id` | string | FK به `products.product_id` |
| `shop_id` | string | FK به `shops.shop_id` |
| `price_toman` | integer-like string/null | مبلغ ثبت‌شده به تومان؛ در Python با Decimal parse شود |
| `last_price_changed_at` | ISO-8601 timestamp/null | آخرین زمان ثبت‌شده تغییر قیمت؛ timezone-aware |
| `seller_title` | string/null | عنوان فروشنده برای آفر؛ می‌تواند از عنوان محصول متفاوت باشد |
| `description` | string/null | توضیح فروشنده؛ غالباً خالی |
| `warranty` | JSON object/null | گارانتی، اگر ثبت شده باشد |

### شکل `warranty`

```json
{"provider":"شرکتی","period_months":6,"description":null}
```

`provider` رشته و `period_months` می‌تواند عدد یا null باشد؛ `description` معمولاً nullable است. وجود warranty object الزاماً به معنی کامل‌بودن همه فیلدها نیست.

## 5. قرارداد مدل Django پیشنهادی

نام داخلی مدل‌ها singular باشد. حفظ source ID مستقل از primary key داخلی مجاز است، اما `source_id` باید unique باشد. پیشنهاد اولیه:

- `Product(source_id unique, persian_title, brand_name nullable, category_name nullable, model nullable, specs JSONField, image_urls JSONField, normalized_title indexed)`.
- `Shop(source_id unique, name, address, location_label, lat, lon, category_names JSONField, contacts JSONField, payment_options JSONField, weekly_hours JSONField, website_url, instagram, supports_fast_delivery nullable)`.
- `Offer(source_id unique, product FK, shop FK, price_toman DecimalField nullable, last_price_changed_at DateTimeField nullable, seller_title, description, warranty JSONField nullable)`.
- `PurchaseMission`, `MissionEvent`, `ContactAttempt` طبق `agent-and-genui.fa.md`.

اگر کلید خارجی به source ID وصل می‌شود، `to_field` و `db_column` را در migration به‌دقت تعریف کنید. نام ستون CSV باید در import map واضح باشد؛ از اتکا به rename جادویی اجتناب کنید.

## 6. قواعد پول و زمان

- مبلغ تومان integer-like است؛ از float استفاده نکنید.
- Django: `DecimalField` با `max_digits` متناسب با outlier مشاهده‌شده و `decimal_places=0`؛ سقف precision بعد از بررسی max واقعی تایید شود.
- API: مبلغ به شکل رشته رقم‌ها مانند `"9460000"` برگردد تا دقت عددی JS از دست نرود.
- UI: formatter با locale فارسی، واحد «تومان» و کنترل null.
- زمان: در DB timezone-aware؛ زمان source در API ISO-8601 با timezone؛ برای UI، timezone موردنظر `Asia/Tehran`.
- `last_price_changed_at` منبع timestamp است، نه زمان تأیید موجودی.

## 7. Import و کیفیت

- streaming CSV + batch size قابل‌تنظیم؛ کل 300MB را در RAM نگه ندارید.
- هر batch transactional باشد یا شکست نیمه‌کاره قابل‌بازیابی باشد.
- اجرای مجدد با همان dataset نباید داده تکراری بسازد.
- گزارش شامل فایل، rows read, inserted, updated, skipped, invalid JSON, duplicate source IDs, orphan FKs، قیمت invalid/outlier و مدت زمان است.
- در صورت orphan، policy باید مشخص باشد: خطای import در حالت strict؛ یا skip+report فقط با flag صریح `--allow-orphans`.
- فایل raw هرگز overwrite نمی‌شود.
