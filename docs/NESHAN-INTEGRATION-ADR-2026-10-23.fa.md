# ADR-007 | انتخاب مشروط نشان برای نقشه و مسیریابی خرید حضوری تهران

**تاریخ:** ۲۳ اکتبر ۲۰۲۶ · **وضعیت تصمیم:** APPROVED FOR IMPLEMENTATION DESIGN / PENDING PROVIDER VALIDATION · **نوع تغییر:** فقط تحقیق و قرارداد پیاده‌سازی، بدون اتصال واقعی یا هزینه API.
**کد مبنا:** `main@e796d7a5aa96` (PRهای #26، #28 و #29 ادغام‌شده‌اند). این ADR بر اساس مستندات عمومی رسمی نشان و قابلیت‌های فعلی پروژه است. حساب نشان و قیمت‌های اختصاصی مشتری مشاهده نشده‌اند.

## تصمیم کوتاه

**نشان** ارائه‌دهندهٔ ترجیحی **مشروط** است: SDK رسمی `@neshan-maps-platform/maplibre-sdk` برای نقشهٔ فارسی و چند نشانگر، Distance Matrix برای مقایسهٔ ETA خودرو/موتورسیکلت و Direction API برای مسیر نهایی. فقط پس از تأیید کلید، هزینه، مسیر اتصال از محیط استقرار، مجوز و نرخ مصرف فعال شود. وضعیت بدون نشان: **فهرست فعلی + آدرس ثبت‌شده + انتخاب فروشنده + فاصله مستقیم به‌صورت مشخص + نقشه OSM فقط opt-in**.

هرگز دادهٔ POI نشان را به‌صورت خام جایگزین Shop دیتاست نکنید: بسیاری از نام‌های فروشگاه‌های مسابقه ساختگی‌اند؛ وجود Offer در CSV، موجودی واقعی نیست؛ مختصات معتبرِ عددی، هویت یک کسب‌وکار را تأیید نمی‌کند. اعتبار محصول/آفر تنها از PostgreSQL و فیلترهای سروری می‌آید.

## مستندات تأییدشده و فاصله تا اثبات عملی

| مورد | از مستندات رسمی | هنوز لازم است |
|---|---|---|
| MapLibre Web SDK | نصب `@neshan-maps-platform/maplibre-sdk`، import CSS، `apiKey`، استایل `light.json`، برچسب فارسی و RTL؛ جغرافیا در SDK به شکل `[lon,lat]` | بررسی پکیج/نسخه قفل‌شده و 320/360/390/1440px، WebGL، CSP، domain allowlist، quota |
| برندینگ SDK | نمایش logo/copyright اجباری و قابل جابه‌جایی ولی غیرقابل حذف | سنجش جایگذاری در RTL موبایل |
| Matrix | `GET https://api.neshan.org/v1/distance-matrix`، هدر `Api-Key`، `origins` و `destinations` به صورت `lat,lon`؛ `type=car|motorcycle`؛ `rows[].elements[].distance.value` متر و `duration.value` ثانیه، `NoRoute` ممکن است | تست واقعی با یک مبدأ و ۳ تا ۵ مقصد از تهران؛ cap عناصر/هزینه از پنل |
| Routing | `GET https://api.neshan.org/v4/direction`، `type=car|motorcycle`، `origin`, `destination` به شکل `lat,lon`؛ `routes[].overview_polyline.points` | تست واقعی ماشین و موتور و خروجی polyline |
| Walking | `GET https://api.neshan.org/v4/direction?type=pedestrian` در صفحه رسمی عابر پیاده، اما نمونه کد صفحه مسیر `/v1/direction` را ذکر می‌کند | **اختلاف نسخه در مستندات**: قبل از کدنویسی با کلید تست شود؛ برای پیاده‌روی از Matrix خودرو ETA نسازید |
| Pricing | مدل `Pay as You Go`؛ صفحه عمومی «اعتبار توسعه ۲۰۰ هزار تومان تا سه ماه» را تبلیغ می‌کند | تعرفه دقیق per-request، احراز شرایط اعتبار، سهمیه واقعی و سقف هزینه حساب تأیید نشده |
| Errors | 470 مختصات، 480 کلید نامعتبر، 481 سقف، 482 نرخ، 483 نوع کلید، 484 scope، 485 سرویس مجاز، 500 خطای نامعلوم | سنجش رفتار واقعی و fallback امن |
| Host accessibility | SDK/REST عمومی مستند شده‌اند | دسترسی سرور مقصد/مرورگر کاربر به دامنه‌های `api.neshan.org` و `static.neshan.org` و آدرس‌های Tiles با CSP واقعی **بررسی نشده** |

**مراجع رسمی، تاریخ مشاهده ۲۳ اکتبر ۲۰۲۶:**
- https://platform.neshan.org/docs/sdk/web/maplibre/neshan-maplibre-gl-js/
- https://platform.neshan.org/docs/api/routing-category/distance-matrix/
- https://platform.neshan.org/docs/api/routing-category/routing/
- https://platform.neshan.org/docs/api/routing-category/routing_pedestrian/
- https://platform.neshan.org/pricing/
- https://platform.neshan.org/tos

## قرارداد UX انتخاب‌شده

1. **بدون origin**: اولین حالت فهرست است، نه ETA. مبدأ به صورت منطقه دستی تهران یا geolocation صرفاً با اقدام کاربر تعیین می‌شود؛ مختصات فعلی کاربر را پیش‌فرض نگیرید.
2. **وجود Offer معتبر، شرط نمایش Pin**: از مجموعه یکسان `offer_ids` مورد قبول `mission_focus`، پس از اعمال فیلتر hard، max 24 آفر و dedupe با `shop_id`. هر Pin قابل اتصال به همان ردیف لیست است.
3. **تمرکز دوطرفه**: `selected_offer_id` و `result_set_id` منبع حقیقت هستند؛ انتخاب pin/list فقط یک اکشنِ versioned و idempotent ایجاد می‌کند. نتیجه قدیمی/race اجازه جابه‌جایی pin فعال را ندارد. نقشه نباید خودکار محصول یا فروشنده جست‌وجو کند.
4. **خرابی نقشه/کلید/Quota/آفلاین**: متن «نمایش نقشه در دسترس نیست؛ فهرست فروشنده‌ها برقرار است»؛ آخرین انتخاب حفظ شود. هیچ زمان سفر محاسبه‌شده جعلی یا نشانگر جابه‌جا شده‌ای نسازید.
5. **ETA اختیاری**: فقط بعد از انتخاب مبدأ و دکمه واضح «محاسبه زمان سفر»، روی ۳ تا ۵ فروشنده واجد شرایط. mode خودرو/موتورسیکلت بر اساس انتخاب کاربر؛ mode پیاده فقط Direction آزمایش‌شده؛ مدت و مسافت `route_distance` را از `straight_line_distance` جدا نمایش دهید.
6. **برچسب شاهد**: `زمان تخمینی با ترافیک از نشان؛ ساعت محاسبه ...؛ احتمال تغییر` و `فاصله مستقیم تقریبی از مبدأ`؛ این‌ها هرگز موجودی، بازبودن واقعی یا هویت فروشگاه را تأیید نمی‌کنند. هر card فروشنده پیام «نام ممکن است ساختگی باشد» را حفظ کند.
7. **سبد مقایسه موبایل**: لیست اول و کنترل نقشه اختیاری با ارتفاع محدود، focus/keyboard قابل آزمون؛ attribution و لوگوی نشان دیده شوند، و reduced-motion رعایت شود.
8. **رضایت و داده**: در اولین بازکردن نقشه توضیح تبادل داده با نشان نمایش داده شود؛ درخواست geolocation مرورگر تنها با اقدام مستقیم؛ lat/lon کاربر در analytics/error logs ثبت نشود. داده در cache با دقت تقلیل‌یافته و TTL کوتاه، نه نگهداری دائمی مسیر فردی.

## قرارداد فنی پیاده‌سازی

**Frontend:** React/Vite، lazy import پکیج SDK و CSS در component `NeshanSellerMap` پس از فعال‌سازی feature flag و رضایت بازکردن نقشه. خود SDK لازم است public **web map key** محدود به دامنه بگیرد؛ این کلید secret مانند REST server key نیست، با این حال نباید کلید نامحدود/REST وارد bundle شود. SDK `map.remove()` روی unmount. markers از `shop.id` و `offer.id`، و آدرس + قیمت فقط از API خود پروژه؛ نه geocoding نام‌های ساختگی.

**Backend:** adapter `NeshanRoutingProvider` و `DisabledRoutingProvider` پشت service boundary؛ REST key فقط در secret manager/متغیر محیطی backend. نقطه و mode را validate کنید؛ انتخاب فروشنده با `result_set_id` و Session/CSRF چک شود و destination **از دیتابیس** resolve گردد، نه از مختصات آزاد کاربر. مبدأ از ورودی explicitly approved و scoped Tehran. از allowlist hostname + GET fixed endpoint برای SSRF پیشگیری شود؛ log ساختاری بدون coordinate یا header secrets.

**قرارداد پیشنهادی (نه endpoint موجود):**
`POST /api/v1/missions/{mission_id}/route-estimates/`
input: `{result_set_id, origin: {lat,lon,source:"manual_region"|"geolocation_opt_in"}, offer_ids: [id1,...id5], mode:"car"|"motorcycle"}`.
output: `{provider:"neshan",mode,measured_at,estimates:[{offer_id,status:"ok"|"no_route"|"unknown_error",duration_seconds?,route_distance_meters?}],availability_verified:false,source:"provider_route_estimate"}`.
اگر feature غیر فعال یا quota/timeout شد: `{provider:"neshan",status:"unavailable",estimates:[]}`، بدون فیلد duration و با UI list fallback. مشخصات نهایی endpoint بعد از spike قرارداد/کلید freeze شوند.

**بهینه‌سازی درخواست:** درخواست Matrix برای ۱ مبدأ × حداکثر ۵ فروشنده، فقط action کاربر؛ debounce و in-flight dedupe؛ caching کوتاه‌مدت با کلید mode+rounded origin+seller ids (فقط با بررسی قوانین cache provider)، timeout و circuit breaker، سقف روزانه و per-session. هیچ retry نامحدود روی 481/482؛ روی 482 backoff کنترل‌شده و روی 481 توقف تا تأیید سهمیه. بدون قیمت دقیق و اندازه‌گیری مصرف، هزینه کل عددگذاری نمی‌شود.

**امنیت/Privacy:** دو کلید مستقل scope شده؛ public map key domain-scoped و محدود، private REST key server-only. محافظت against IDOR, CSRF, outbound SSRF, rate limiting؛ CSP/attribution/terms. برای مختصات جعلی فروشگاه تطبیق live POI یا تأیید «باز است» ادعا نشود.

## Gateهای دقیق قبل از فعال‌سازی یا ادغام کد

- G1: کاربر حساب و کلیدهای مجاز را در محیط امن خود ایجاد و سقف/تعرفه را از پنل تأیید کند؛ هرگز کلید به Git یا chat وارد نشود.
- G2: اسپایک **غیرعمومی با حداقل مصرف** روی ۳ مسیر تهران (مختصات فروشگاه از ZIP)، Matrix car و Direction car/motorcycle و pedestrian به صورت جدا، و سنجش از سرور استقرار؛ تفاوت endpoint پیاده‌روی resolve شود.
- G3: نقشه MapLibre RTL با ۲۴ pin و index مشترک لیست، تست geolocation denied، network failed، 481/482، invalid API key، keyboard/focus, 320/360/390/1440؛ تست‌ها با mock/fixture اجرا شوند و CI به سرویس پولی دست نزند.
- G4: zero hard-filter violation، source labels درست، zero fabricated route/ETA، حفظ کلیه actions در صورت failure، ۱۲ E2E و ۲۰ edge از ماتریس رسمی پروژه.
- G5: یک CI کامل روی SHA ثابت بعد از بستهٔ کد اجرایی؛ **برای این ADR اسناد-only هیچ CI جدیدی اجرا نمی‌شود**.

**مرز ادعا:** تا تکمیل G1/G2، نشان فقط انتخاب مشروط است، «متصل‌شده» یا ETA قابل استفاده نیست. حتی با قبولی همه گیت‌ها، فروشگاه‌های ساختگی دیتاست مقصد واقعیِ تأییدشده برای مراجعه نخواهند شد.
