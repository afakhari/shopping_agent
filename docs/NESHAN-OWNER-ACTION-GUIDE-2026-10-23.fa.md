# راهنمای اقدامات مالک پروژه برای اتصال واقعی نشان به بازارکامپس

> **تصمیم جدید مالک: بدون خرید اعتبار نشان.** این سند مسیر اختیاریِ پولی را صرفاً به‌عنوان سابقه فنی توضیح می‌دهد و **برای نسخه فعلی نباید مراحل خرید اعتبار، آزمایش پولی یا فعال‌سازی Neshan انجام شوند**. مبنای محصول رایگان در [ZERO-CREDIT-MAPS-2026-10-23.fa.md](ZERO-CREDIT-MAPS-2026-10-23.fa.md) ثبت شده است. کلید REST قبلی می‌تواند بدون مصرف باقی بماند و در محیط انتشار لازم نیست.


> **به‌روزرسانی بعد از اعلام مالک:** دو سرویس «ماتریس فاصله با ترافیک» و «مسیریابی با ترافیک + ETA» در پنل انتخاب شده‌اند و کلید REST ساخته شده است. نیازی نیست این دو را دوباره ایجاد کنی. هنوز معلوم نیست کلید وب مخصوص React/OpenLayers ساخته شده باشد. راهنمای نصب نقشه: [تصمیم React/OpenLayers](NESHAN-REACT-OPENLAYERS-PLAN-2026-10-23.fa.md).

**تاریخ:** ۲۳ اکتبر ۲۰۲۶ · **اولویت:** کاربرد واقعی در تهران، هزینه قابل پیش‌بینی، عدم گمراهی کاربران، بدون افشای کلید. این سند دستورالعمل اجرای مالک است، نه مدرک فعال‌بودن حساب نشان.

## الان چه چیزهایی کار می‌کنند؟

- PRهای #26، #28، #29 و #30 در main ادغام شده‌اند: گفت‌وگوی زمینه‌ای، انتخاب فروشنده، فهرست و نقطه OSM اختیاری، شبیه‌سازی تماس، و adapter مسیریابی نشان **پیش‌فرض خاموش**.
- این PR لینک **بدون کلید** به نقطه ثبت‌شده و (پس از انتخاب مبدأ دستی) مسیر خودرو در اپ/وب نشان را اضافه می‌کند. این لینک‌ها API billable پروژه را فراخوانی نمی‌کنند.
- **هنوز نیست:** نقشه چندپین SDK نشان، تأیید عملی provider از هاست مقصد، زمان سفر واقعی در خود سایت، مسیر پیاده با آزمایش واقعی، استقرار HTTPS تأییدشده و UX کاربر واقعی.
- نام بخش بزرگی از فروشگاه‌های dataset و تمامی شماره‌های تماس طبق متن چالش ساختگی است؛ این مسیر برای **دموی مسابقه/مختصات ثبت‌شده** است، نه اثبات محل کسب‌وکار موجود.

## گام ۱: ایجاد حساب و دریافت کلیدهای درست

1. وارد **https://platform.neshan.org/panel/login** شو (از صفحه رسمی https://platform.neshan.org/pricing/ به «ثبت‌نام رایگان» نیز می‌رسی).
2. ورود/ثبت‌نام را با اطلاعات خودت انجام بده. توافق‌نامه و مقررات را بخوان؛ هزینه بر پایه مصرف است و اعتبار آزمایشیِ تبلیغ‌شده به‌معنای تخصیص قطعی به حساب تو نیست.
3. در پنل، یک برنامه/وب‌سایت برای **Map SDK** بساز و **کلید Web Map** جداگانه بگیر؛ آن را فقط برای دامنه‌ای که سایت واقعاً روی آن منتشر می‌شود محدود کن. **نقشه SDK هنوز در این PR به فرانت‌اند وصل نشده است**، پس واردکردن کلید وب در .env فعلی نقشه جدیدی ظاهر نمی‌کند.
4. برای **REST Distance Matrix**، کلید مناسب آن سرویس بگیر. نوع و scope آن را با راهنمای رسمی مطابقت بده. کلید REST را فقط در backend/deployment secret ذخیره کن، نه در `VITE_*`، `frontend/`، Dockerfile، GitHub PR/Issue یا گفتگو.
5. از پنل/بخش گزارش‌ها، *بدون اشتراک رمز یا کلید* این اطلاعات را برای برنامه‌ریزی ثبت کن: `has_web_map_key`، `has_rest_matrix_key`، `allowed_domain`، `matrix_price_per_request_or_element`، `monthly_budget_toman`، `daily_quota`، `allowed_services` و `hosting_provider`.

**مراجع رسمی:** https://platform.neshan.org/docs/sdk/web/maplibre/neshan-maplibre-gl-js/ ، https://platform.neshan.org/docs/api/routing-category/distance-matrix/ ، https://platform.neshan.org/pricing/ . نرخ‌های حساب خودت در پنل مرجع نهایی هستند.

## گام ۲: بررسی هاست و دامنه

- نام هاست نهایی (مثلاً Liara یا VPS) و **دامنه HTTPS واقعی خودت** را تعیین کن؛ اگر هنوز نداری، آماده‌سازی production ناتمام است. فایل `compose.production.yaml` فقط برای اجرای Docker پشت reverse proxy دارای TLS نوشته شده و manifest لیارا نیست.
- در firewall/DNS هاست باید دسترسی به `https://api.neshan.org` برای backend برقرار باشد؛ نقشه وب بعداً به دامنه‌های style/tiles نشان از مرورگر کاربران نیاز دارد. در محیط میزبانی واقعی تست شود.
- سرور باید migration `0006_routing_daily_usage` را اجرا کرده باشد؛ بدون آن فعال‌سازی مسیریابی امن نیست.
- تمام فروشندگان فقط در تهران و با آفر معتبر پروژه نمایان شوند. اتصال به سرویس نقشه «موجودی امروز»، «فروشگاه حقیقی» یا «قیمت فعلی» را تأیید نمی‌کند.

## گام ۳: آزمون بی‌هزینه روی سیستم خودت

پس از `git pull` نسخه ادغام‌شده پروژه، در ریشه repo:

```powershell
py -3 scripts/neshan_smoke.py
```

نتیجه مورد انتظار: `DRY_RUN=PASS; NESHAN_REQUESTS=0`. این فقط ایمنی اسکریپت را تأیید می‌کند و هیچ نتیجه‌ای درباره اتصال یا اعتبار کلید نیست.

## گام ۴: دقیقاً یک تست واقعی با اجازه خودت

**فقط اگر تعرفه واقعی را دیده‌ای و حتی هزینه یک درخواست را پذیرفته‌ای.** در PowerShell، بدون چاپ‌شدن کلید:

```powershell
$secret = Read-Host "Private Neshan REST Matrix key" -AsSecureString
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret)
try {
  $env:NESHAN_ROUTING_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
  py -3 scripts/neshan_smoke.py --service matrix --live --authorize-one-call
  # این فرمان جداگانه احتمالاً هزینه یک درخواست جدید دارد؛
  # فقط بعد از تأیید مستقل سهمیه مسیریابی:
  # py -3 scripts/neshan_smoke.py --service direction --live --authorize-one-call
} finally {
  Remove-Item Env:NESHAN_ROUTING_API_KEY -ErrorAction SilentlyContinue
  [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
}
```

- حداکثر **یک درخواست Matrix car با دو مختصات ثابت در تهران** ارسال می‌شود. موفقیت باید `LIVE_RESULT=PASS`، `NESHAN_REQUESTS=1` و زمان/مسافت دارای مقدار داشته باشد.
- در صورت خطای `480` کلید، `483` نوع کلید، `484` scope، `485` سرویس مجاز، `481` اعتبار/سقف و `482` نرخ درخواست را در **پنل/پشتیبانی نشان** بررسی کن. درخواست را خودکار تکرار نکن.
- با اجرای آزمون از **هاست مقصد** (نه فقط لپ‌تاپ خودت)، نتیجه دسترسی واقعی backend روشن می‌شود.
- فقط **وضعیت PASS یا HTTP code سانسورشده** و نوع هاست را به تیم بگو؛ خود کلید، Authorization header یا فایل .env را ارسال نکن.

## گام ۵: فعال‌سازی آزمایشی بک‌اند پس از PASS و تأیید هزینه

در تنظیمات خصوصی **فقط محیط backend** (نه repository) مقدارهای زیر را پس از تأیید سهمیه قرار بده. اعداد ۱ و ۲ صرفاً مثال **سقف بسیار محدود آزمایش** هستند، نه نسخه production:

```dotenv
NESHAN_ROUTING_ENABLED=1
# فقط پس از موفقیت smoke جداگانه Direction و تأیید هزینه:
NESHAN_DIRECTION_ENABLED=0
NESHAN_ROUTING_API_KEY=<PRIVATE_REST_KEY_IN_HOST_SECRETS>
NESHAN_ROUTING_MAX_CALLS_PER_MISSION=1
NESHAN_ROUTING_DAILY_MAX_CALLS=2
```

- ابتدا migration پروژه را اجرا کن، سپس backend را restart/redeploy کن.
- بدون فروشنده منتخب یا قبل از انتخاب مبدأ تهران، هیچ درخواست route نزن. GET capability صرفاً وضعیت را اعلام می‌کند؛ POST route estimate از سهمیه کم می‌کند، حتی اگر provider خطا بدهد.
- در یک مأموریت تازه با حداقل دو آفر، مبدأ دستی تهران را انتخاب کن، فهرست فروشندگان را باز کن، دکمه محاسبه را **یک‌بار** بزن و در پنل نشان مصرف را بررسی کن.
- اگر مشکل امنیتی/هزینه/داده‌ای دیدی، `NESHAN_ROUTING_ENABLED=0` و backend restart. فهرست فروشندگان و لینک‌های نقطه همچنان کار می‌کنند.
- سقف روزانه فعلی **تعداد درخواست** را محدود می‌کند، نه قیمت ریالی یا تعداد عناصر محاسباتی سرویس؛ نرخ واقعی و هزینه ۱×۵ مقصد باید قبل از استفاده عمومی از پنل تأیید شوند.

## گام ۶: کلید نقشه وب و تکمیل نقشه چندپین

این مرحله هنوز به کد نیاز دارد و با افزودن کلید به سرور به‌تنهایی فعال نمی‌شود. بعد از آماده‌بودن دامنه و کلید وب محدودشده، باید `@neshan-maps-platform/maplibre-sdk` با نسخه قفل‌شده نصب شود و نقشه React پس از اقدام کاربر و فقط در مرورگر mount شود؛ markers فقط از offer/shopهای واجد شرایط همان result_set، با انتخاب دوطرفه pin/list و fallback فهرست. لوگو و attribution نشان **نباید مخفی شوند**. کلید نقشه عمومیِ محدود به دامنه باید از کلید خصوصی REST کاملاً جدا بماند.

## گام ۷: مراحل تحویل و UX مسابقه

- [ ] اجرای real ZIP smoke روی هاست مقصد، تأیید رقم ۲۲۵٬۹۰۳ محصول و ۳۳۱٬۵۰۶ آفر؛ هیچ اطلاعات خام در مخزن Git ذخیره نشود.
- [ ] ۵۰ query با relevance انسانی (seed خودکار gold نیست)، ۱۲ journey مستقل و ۲۰ edge؛ keyboard و mobile ۳۲۰/۳۹۰/۱۴۴۰.
- [ ] HTTPS عمومی، session/cookie/CSRF، quotaهای مدل، لاگ بدون کلید و مختصات حساس، بازیابی خطای شبکه و محتوای accessibility.
- [ ] تست روی حداقل ۵ کاربر مستقل، رفع نقاط سردرگمی و ضبط ویدئوی پنج دقیقه از همان نسخه منتشرشده.
- [ ] متن دمو هرگز فروشگاه ساختگی را به‌عنوان فروشگاه واقعی، استعلام شبیه‌سازی را تماس واقعی یا Matrix زمان سفر را تأیید موجودی معرفی نکند.

## دقیقاً چه اطلاعات غیرمحرمانه‌ای برای ادامه پروژه لازم است؟

```text
Hosting: Liara / VPS / Other
Production HTTPS domain: <public-domain-or-not-yet>
Neshan Web SDK key created? yes/no
Neshan REST Matrix key created? yes/no
REST service and domain whitelist approved? yes/no
Account quota and pricing checked? yes/no
Maximum approved daily budget (toman): <number-or-undecided>
One-call host smoke: PASS / HTTP code / not-run
```

کلیدهای خام، شماره تماس، فایل .env و اطلاعات ورود را **هرگز** در متن گفتگو یا Issue ثبت نکن.


## مرحله خاص بعد از فعال‌سازی دو سرویس REST توسط مالک

1. با کلید کنونی، در هاست مقصد ابتدا smoke **Matrix** و سپس (فقط با اجازه پرداخت جدید) smoke **Direction** را جداگانه اجرا کن. هر فرمان دقیقاً یک درخواست به endpoint مربوطه دارد و حاوی موقعیت کاربر واقعی نیست.
2. بعد از PASS هر دو و تأیید سهمیه واقعی، `NESHAN_DIRECTION_ENABLED=1` را در secret/config محیط سرور بگذار؛ با خاموش بودن `NESHAN_ROUTING_ENABLED` هر دو همچنان خاموش‌اند. سقف مشترک درخواست روزانه شامل Matrix و Direction می‌شود.
3. برای نقشه React/OpenLayers نشان به **یک کلید وب جداگانه** نیاز است؛ فعال کردن سرویس‌های REST به معنی مجازبودن `mapKey` وب نیست. بدون کلید و تست بسته‌های npm و lockfile، در کد فعلی نقشه هنوز OSM اختیاری است.
4. چون کاربر کلید REST ساخته است، **مهم‌ترین اطلاعات غیرمحرمانه باقی‌مانده** عبارت است از: `web_map_key_created=yes/no`، نام نوع هاست، وضعیت دامنه HTTPS، تعرفه و اعتبار پنل، `smoke_matrix=PASS|not-run|HTTP-code` و `smoke_direction=PASS|not-run|HTTP-code`. **خود کلید و عکس آن را ارسال نکن.**
