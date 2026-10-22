# قرارداد API — نسخه `v1`

**وضعیت:** قرارداد نسخه اول. Endpointهای سلامت، جست‌وجوی کاتالوگ، جزییات محصول/آفر و فروشگاه اکنون در کد پیاده‌سازی شده‌اند؛ اجرای runtime تا نصب dependencies و اجرای تست‌ها هنوز [NOT VERIFIED] است. APIهای مأموریت، SSE و شبیه‌ساز تماس در Sprint 2 نوشته شده‌اند؛ runtime آن‌ها هنوز به دلیل نبود Django در محیط ساخت تأیید نشده است. parser عامل از adapter اختیاری سازگار با OpenAI استفاده می‌کند و در صورت عدم پیکربندی یا خطا به heuristic deterministic برمی‌گردد؛ runtime provider در این محیط تأیید نشده است.

## 1. قواعد عمومی

- prefix: `/api/v1/`.
- UTF-8 JSON؛ timezone ورودی/خروجی تاریخ ISO-8601.
- مبالغ تومان به صورت رشته ارقام صحیح (مثلاً `"9460000"`) تا از محدودیت precision در JavaScript جلوگیری شود.
- شناسه‌های source به صورت string حفظ می‌شوند.
- ورودی‌های query و body با DRF Serializer/Pydantic schema اعتبارسنجی شوند.
- صفحه‌بندی پیش‌فرض `page=1`, `page_size=20`; بیشینه `page_size=50`.
- همه نتایج محصول باید دارای آفر و فروشگاه واجد شرایط در مجموعه تهران باشند؛ نتیجه بدون offer واجد شرایط به UI اصلی ارسال نشود.
- endpoint جست‌وجو/facet/filter deterministic است و نباید LLM را صدا بزند.

## 2. Endpointهای نسخه اول

| Method | Path | مسئولیت | وابستگی LLM |
|---|---|---|---|
| GET | `/health/live/` | زنده‌بودن process | خیر |
| GET | `/health/ready/` | بررسی readiness وابستگی‌های ضروری | خیر |
| GET | `/catalog/search/` | جست‌وجوی محصول با آفرهای واجد شرایط | خیر |
| GET | `/products/{product_id}/` | جزئیات محصول | خیر |
| GET | `/products/{product_id}/offers/` | آفرهای محصول با فیلتر/مرتب‌سازی | خیر |
| GET | `/shops/{shop_id}/` | جزئیات و آدرس فروشگاه | خیر |
| POST | `/missions/` | ساخت مأموریت از درخواست اولیه | بله، در مسیر agent-enabled؛ باید خطای provider قابل مدیریت باشد |
| GET | `/missions/{mission_id}/` | snapshot مأموریت | خیر |
| POST | `/missions/{mission_id}/turns/` | پردازش نوبت و ارسال event stream | معمولاً بله |
| POST | `/missions/{mission_id}/contact-attempts/` | درخواست ابزار شبیه‌سازی تماس در مأموریت | نه الزاماً؛ نتیجه از simulator |

Prefix نهایی اسلش‌دار است. اگر پروژه policy بدون slash انتخاب کند باید این سند و کلاینت یکجا اصلاح شود؛ هر دو سبک را مخلوط نکنید.

## 3. `GET /catalog/search/`

### پارامترها

| نام | نوع | پیش‌فرض/محدودیت | معنا |
|---|---|---|---|
| `q` | string | اجباری، 1..200 کاراکتر | عبارت محصول یا کاربرد |
| `max_price_toman` | integer-string | اختیاری، >= 0 | سقف قیمت؛ روی آفرهای قابل‌رتبه‌بندی اعمال شود |
| `must_have_in_person_credit` | boolean | `false` | تنها shop دارای option `channel=in_person` |
| `lat` | decimal | اختیاری همراه `lon` | مبدأ کاربر |
| `lon` | decimal | اختیاری همراه `lat` | مبدأ کاربر |
| `radius_m` | integer | اختیاری؛ بازه امن تعریف شود | شعاع مجاز حول مبدأ |
| `sort` | enum | `relevance` | `relevance`, `price_asc`, `distance_asc`, `recent_price_change` |
| `page` | integer | 1 | صفحه |
| `page_size` | integer | 20; max 50 | اندازه صفحه |

اعتبارسنجی: `lat` و `lon` باید با هم بیایند؛ `radius_m` بدون مختصات مبدأ نادیده گرفته نشود، بلکه خطای validation بدهد. `distance_asc` بدون مختصات نامعتبر است. اگر `max_price_toman` داده شده، آفر بدون قیمت یا قیمت پرچم‌خورده وارد نتیجه قیمت‌محور نمی‌شود.

### پاسخ پیشنهادی

```json
{
  "query": "هدفون",
  "filters": {
    "max_price_toman": "30000000",
    "must_have_in_person_credit": false,
    "radius_m": null
  },
  "page": 1,
  "page_size": 20,
  "total": 125,
  "results": [
    {
      "product": {
        "id": "product_example",
        "title": "عنوان واقعی از دیتاست",
        "brand": null,
        "category": "هدفون",
        "model": null,
        "images": [],
        "specs": []
      },
      "best_offer": {
        "id": "offer_example",
        "price_toman": "25000000",
        "last_price_changed_at": "2026-10-10T10:00:00Z",
        "price_quality": "stale",
        "shop": {
          "id": "shop_example",
          "name": "نام از دیتاست",
          "address": "نشانی از دیتاست",
          "lat": 35.7,
          "lon": 51.4,
          "distance_m": null,
          "accepts_in_person_credit": false
        }
      },
      "eligible_offers_count": 3,
      "reasons": ["تطبیق عبارت جست‌وجو", "داخل سقف بودجه"]
    }
  ],
  "intent_hint": null
}
```

این فقط قرارداد نمونه است؛ شناسه‌ها و داده‌های example واقعی نیستند. `total` تعداد محصولات یکتای واجد شرایط پس از تمام شروط سخت است، نه تعداد آفرها. هر محصول می‌تواند چند آفر داشته باشد و `best_offer` باید با policy مرتب‌سازی تعریف شود.

### دامنه‌گذاری قصد برای عبارت‌های مبهم

برای جست‌وجوی عمومی `فشارسنج`، API نتایج دسته `فشارسنج پزشکی` را پیش‌فرض می‌کند و در `intent_hint` گزینه‌ای برای جست‌وجوی صنعتی/محیطی برمی‌گرداند. عبارت‌هایی مثل `فشارسنج صنعتی` به دسته‌های صنعتی محدود می‌شوند. جست‌وجوهای مشخص برند/مدل که با قواعد حوزه‌ای تطبیق ندارند، به‌صورت خودکار محدود نمی‌شوند. جزئیات و دلیل این policy در [سند دامنه‌گذاری قصد جست‌وجو](search-intent-scope.fa.md) آمده است.

## 4. جزئیات محصول و آفر

`GET /products/{product_id}/` باید 404 بدهد اگر شناسه ناموجود است. پاسخ محصول شامل title، brand nullable، category، model، images و specs خامِ parseشده است.

`GET /products/{product_id}/offers/` پارامترهای `must_have_in_person_credit`, `max_price_toman`, `lat`, `lon`, `radius_m`, `sort`, `page`, `page_size` را می‌پذیرد. هر آفر با shop و وضعیت eligibility برمی‌گردد. فیلتر شرط سخت باید در query اعمال شود نه فقط در UI.

`GET /shops/{shop_id}/` آدرس، مختصات، category_names، contacts، weekly_hours، payment_options و لینک‌های ثبت‌شده را برمی‌گرداند. وجود فیلد null باید صریح باقی بماند.

## 5. مأموریت و stream

### ساخت مأموریت

`POST /missions/` body نمونه:

```json
{
  "initial_message": "یک هدفون برای مترو تا سی میلیون می‌خواهم",
  "constraints": {"city": "tehran"},
  "client_request_id": "optional-idempotency-key"
}
```

خروجی: `mission_id`, `status`, `current_stage`, `created_at`, و در صورت نیاز initial UI payload. استفاده از شناسه ناشناس/session برای نسخه داوری کفایت می‌کند؛ ورود/ثبت‌نام خارج از محدوده است.

### نوبت مأموریت

`POST /missions/{mission_id}/turns/` با body `{ "message": "...", "client_request_id": "..." }` می‌تواند stream از نوع `text/event-stream` برگرداند. کلاینت از `fetch` استفاده کند (زیرا EventSource استاندارد body برای POST نمی‌فرستد). در فیلد `constraints` این endpoint، مقدار صریح `max_price_toman: null` برای پاک‌کردن سقف بودجه ذخیره‌شده استفاده می‌شود؛ حذف کلید به‌تنهایی مقدار قبلی را حفظ می‌کند.

هر event یک envelope با schema version دارد:

```json
{"schema_version":1,"mission_id":"m_example","seq":4,"type":"stage","payload":{"stage":"searching"}}
```

رویدادهای حداقلی در `agent-and-genui.fa.md` تعریف شده‌اند. کلاینت باید `seq`های تکراری را deduplicate کند و پس از قطع اتصال بتواند snapshot مأموریت را از GET بخواند.

رویداد `ui.component` شامل `payload.component` و `payload.data` است. برای چند قطعه هم‌زمان، `component` برابر `component_stack` و `data.components` آرایه‌ای از `{ type, id?, data }` است. فرانت‌اند فقط کامپوننت‌های ثبت‌شده را می‌سازد؛ فیلد ناشناخته یا component نامعتبر به fallback امن می‌رود و هیچ HTML/JavaScript از payload اجرا نمی‌شود. حالت‌های `clarification_form`، `category_choice`، `empty_state` و `visit_plan` نمونه‌های فعلی‌اند. پاک‌کردن budget باید با مقدار صریح `null` انجام شود؛ حذف کلید به‌تنهایی به معنی حفظ مقدار قبلی است.

## 6. ابزار تماس

`POST /missions/{mission_id}/contact-attempts/` body:

```json
{"shop_id":"shop_example","offer_id":"offer_example","purpose":"verify_availability"}
```

پاسخ شامل `attempt`, `alternatives`, `alternative_products`, `events` و `mission` است. `alternatives` آفرهای دیگر همان محصول از فروشگاه‌های دیگر را دارد؛ `alternative_products` مجموعه نتیجه جست‌وجوی محصولات جانشین با شکل DTO جست‌وجوی کاتالوگ است. تنها گزینه‌های واجد شرایط شروط فعلی بازگردانده می‌شوند. در حال حاضر فقط `verify_availability` پیاده شده؛ purpose قیمت/ساعت کاری در serializer رد می‌شود تا outcome موجودی به‌اشتباه به آن‌ها نسبت داده نشود.

کلاینت **حق ندارد** `outcome`, `response_text`, `scenario_result` یا هر فیلدی که نتیجه را انتخاب می‌کند بفرستد. سرور simulator fixture را براساس `DEMO_CONTACT_OUTCOMES` و تعداد تلاش‌های همان مأموریت انتخاب می‌کند و `ContactAttempt` + event را ذخیره می‌کند. در صورت شکست، پاسخ شامل `alternatives` (فروشگاه‌های دیگر همان محصول) و `alternative_products` (محصولات جانشین دارای آفر منطبق در همان دسته/عبارت) است. شناسه محصولات جانشین به candidateهای مأموریت افزوده می‌شود تا قابل استعلام بعدی باشند. در نسخه فعلی فقط `purpose=verify_availability` پیاده شده؛ purposeهای قیمت و ساعت کاری رد می‌شوند تا نتیجه گمراه‌کننده تولید نشود.

## 7. خطاها

قرارداد واحد:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "پارامترهای ورودی معتبر نیستند.",
    "details": {"lat": ["lon نیز الزامی است."]},
    "request_id": "req_example"
  }
}
```

کدهای حداقلی: `VALIDATION_ERROR` (400)، `NOT_FOUND` (404)، `CONFLICT` (409)، `RATE_LIMITED` (429)، `DEPENDENCY_UNAVAILABLE` (503)، `INTERNAL_ERROR` (500). متن توسعه/stack trace فقط در log بماند.

## 8. امنیت و سازگاری

- CORS فقط originهای لازم.
- API key/secret فقط در environment server.
- ورودی متن طبیعی در log کامل ذخیره نشود مگر ضرورت روشن؛ PII redact شود.
- تمام UI payloadها schema validate شوند؛ نوع کامپوننت از allowlist.
- `schema_version` برای UI event و API responseهای حساس به قرارداد.
- تغییر breaking به `/api/v2/` یا تغییر نسخه قرارداد نیاز دارد؛ در این پروژه کوچک، هم‌تغییری frontend/backend پذیرفته است اما schema باید مستند بماند.


### وضعیت تازگی قیمت (`price_quality`)

- `recent_change`: زمان آخرین تغییر ثبت‌شده در هفت روز گذشته است؛ این وضعیت موجودی امروز یا صحت لحظه‌ای قیمت را تضمین نمی‌کند.
- `stale`: آخرین تغییر ثبت‌شده بیش از هفت روز قبل بوده است.
- `unknown_timestamp`: قیمت ثبت شده اما زمان تغییر در داده مشخص نیست.
- `unknown_price`: مبلغ آفر ثبت نشده است.

موجودی زنده مستقل از این فیلد است و تا زمانی که تماس/استعلام (واقعی یا سناریوی شبیه‌سازی‌شده مشخص) نتیجه‌ای نداشته باشد نباید تأییدشده فرض شود.


## 9. وضعیت واقعی اجرای مأموریت در MVP

`POST /missions/{mission_id}/turns/` با `fetch` + `Accept: text/event-stream` رویدادهایی با envelope نسخه‌دار می‌دهد. هر event دارای `schema_version`, `mission_id`, `seq`, `type`, `payload` است. رویدادهای فعلی شامل `user.message`, `stage`, `assistant.message`, `ui.component` و `turn.completed` هستند. stream در این نسخه eventهای ذخیره‌شده پس از اجرای deterministic graph را ارسال می‌کند؛ نه stream توکن مدل یا رویداد زنده هر node.

`POST /missions/{mission_id}/contact-attempts/` فقط `shop_id`, `offer_id` و `purpose` را می‌پذیرد. هر فیلدی مانند `outcome` یا `scenario_index` که از کلاینت برای انتخاب نتیجه ارسال شود، رد می‌شود. نتیجه از ترتیب server-side در `DEMO_CONTACT_OUTCOMES` و شمار تلاش‌های همین مأموریت انتخاب می‌شود. مقدار `source_type=demo_simulation` همیشه در رکورد باقی می‌ماند.

`GET /missions/{mission_id}/` شامل snapshot و حداکثر ۱۰۰ event نخست است. برای UI نسخه اول کافی است؛ اگر مأموریت بیش از ۱۰۰ event داشته باشد، باید endpoint pagination یا پارامتر `after_seq` اضافه شود.
