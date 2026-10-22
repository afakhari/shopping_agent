# سند جامع توسعه محصول و مهندسی «بازارکامپس»

**نسخه سند:** ۱٫۰ · **تاریخ:** ۳۰ مهر ۱۴۰۵ / ۲۲ اکتبر ۲۰۲۶
**وضعیت:** معماری و برنامه توسعه مصوب پیشنهادی؛ با پیاده‌سازی نهایی اشتباه نشود.
**دامنه:** دستیار هوشمند خرید حضوری در تهران، مبتنی بر دیتاست رسمی چالش ترب.
**تصمیم کلیدی:** Modular Monolith، معماری تعامل Hybrid Workspace، شبیه‌ساز سروریِ قابل‌بازتولید و داده‌محور، بازسازی مرحله‌ای فرانت‌اند و گردش‌کار ایجنت.
**سند مرجع نیاز:** `docs/blueprint/CHALLENGE-TRACEABILITY.fa.md` و شرح رسمی کاربر.

> این سند یک قرارداد توسعه است: آنچه «باید ساخته شود» را از آنچه «هم‌اکنون در آرشیو کد وجود دارد» جدا می‌کند. داده برگزارکننده در جهان شبیه‌سازی مسابقه معتبر تلقی می‌شود؛ نتیجه استعلام شبیه‌سازی‌شده از تماس واقعی بیرونی تفکیک می‌شود. اجرای واقعی Django، مدل، نقشه، import CSV و دیپلوی هنوز در این بسته تأیید نشده است.

## ۰. خلاصه مدیریتی و تصمیم بازسازی

بازارکامپس باید در کمتر از چند تعامل کاربر را از «نمی‌دانم چه بخرم» به «محصول و فروشگاه مناسب را انتخاب کرده‌ام، شرایط مراجعه را می‌دانم و گزینه پشتیبان دارم» برساند. **چت ابزار ورود و توضیح است، نه تنها سطح تعامل.** هسته محصول یک فضای تصمیم‌گیری واکنش‌گرا شامل انتخاب محصول، مقایسه، فهرست و نقشه فروشگاه‌ها، استعلام و برنامه مراجعه است.

**تصمیم فنی:** Django/DRF/PostgreSQL و React/TypeScript/Vite را به دلیل تناسب با اندازه چالش حفظ می‌کنیم. کد موجود مبنای قطعیِ معماری نیست: اگر تست‌ها یا تحلیل ساختاری نشان دهند یک ماژول ضعیف است، بدون حفظ API داخلی آن بازسازی می‌شود؛ اما مهاجرت کورکورانه همه فریم‌ورک‌ها رد می‌شود. الگوریتم retrieval و منطق eligibility در سرویس‌های قطعی، LLM فقط برای فهم، پرسش ضروری و توضیح قابل‌اتکا استفاده می‌شود. LangGraph مأموریت چندمرحله‌ای را هدایت می‌کند؛ checkpoint پایدار و idempotency قبل از اجرای تماس ضروری است.

**دلیل سرمایه‌گذاری:** از ۳۰۰ امتیاز چالش، محصول و UX هر کدام ۷۵، هوشمندی ۵۰، دیپلوی ۴۰، پیاده‌سازی ۴۰ و استفاده از دیتاست ۲۰ امتیاز دارند؛ در نتیجه UX و تکمیل سفر خرید وزن بیشتری از نمایش پیچیدگی معماری دارند.

### ۰.۱ اهداف غیرقابل‌مذاکره

1. تمام پیشنهادهای قابل خرید به Product → Offer → Shop معتبر ارجاع داشته باشند؛ دسته فعالیت فروشگاه دلیل موجودی محصول نیست.
2. محدودیت‌های سخت کاربر، از جمله بودجه، خرید اعتباریِ واجد شرایط، مکان و مشخصات الزامی، به‌صورت سروری اعمال شوند. در صورت صفر نتیجه، سیستم بی‌اجازه محدودیت را شل نکند.
3. قیمت ثبت‌شده، زمان آخرین *تغییر* قیمت، وضعیت استعلام و موجودی تأییدشده مفاهیم جدا باشند.
4. شبیه‌سازی فروشنده توسط سرور و fixture قابل‌بازتولید هدایت شود؛ کلاینت نتواند outcome دلخواه تعیین کند.
5. مسیر کار با قطع ارتباط، عدم پاسخ فروشنده، نبود نتیجه، نبود نقشه و بازگشت کاربر ناتمام نماند.
6. رابط به فارسی معیار، RTL، دسترس‌پذیر و mobile-first باشد؛ کاربر برای انجام کارهای ساختاریافته ناچار به نوشتن پرامپت مجدد نباشد.
7. عملکرد نسخه مستقر و دمو ۵ دقیقه‌ای با تست end-to-end تأیید شود؛ ظاهر به تنهایی معیار تکمیل نیست.

### ۰.۲ خارج از محدوده نسخه مسابقه

پرداخت واقعی، خرید آنلاین و سبد پرداخت؛ رزرو قطعی کالا بدون کانال رسمی؛ ربات تماس تلفنی واقعی با فروشگاه‌های دارای شماره ساختگی؛ نقشه طبقات داخلی پاساژ بدون داده نقشه داخلی؛ پوشش سراسری ایران؛ ثبت‌نام اجباری؛ تشخیص قطعی محصول از عکس؛ مدل چندعاملی خودمختار بدون نیاز روشن؛ زیرساخت microservices؛ تشخیص موجودی قطعی صرفاً از ثبت Offer. قابلیت چندقلمی و جست‌وجوی تصویری فقط پس از تثبیت P0 قابل توسعه‌اند.

## ۱. مبانی مستند و کیفیت داده

**منبع رسمی چالش:** تمام فروشگاه‌ها تهران‌اند، اما نمونه فقط حدود ۱۰٪ فروشگاه‌های تهرانِ ترب را پوشش می‌دهد و منطقه‌بندی گزینشی است. ۶۳۶۴ نام فروشگاه و تمام شماره‌ها در مجموعه ساختگی‌اند؛ در این مسابقه داده‌های ارائه‌شده مبنای واقعیت محیط شبیه‌سازی هستند. ۱۱۲ فروشگاه با وب‌سایت/اینستاگرام معتبرِ دیتاست نام اصلی دارند. محصول و آفر باید از همان شناسه‌های ورودی خوانده شوند. این‌ها ویژگی دامنه مسابقه‌اند، نه مجوز ادعای تماس واقعی در بیرون از شبیه‌ساز.

**گزارش ممیزی موجود در آرشیو** (`reports/dataset-audit.json`، تولیدشده در ۲۱ اکتبر ۲۰۲۶؛ نه شمارش جدید CSV در این بسته):

| شاخص | مقدار گزارش‌شده | پیامد |
|---|---:|---|
| محصولات یکتا | ۲۲۵٬۹۰۳ | بازیابی و دسته‌بندی پایدار |
| فروشگاه‌ها | ۶٬۴۷۶ | جست‌وجو و نقشه تهران |
| آفرها | ۳۳۱٬۵۰۶ | join قطعی Product/Shop |
| محصولات با تصویر | ۲۲۴٬۶۸۴ | UI بصری اولویت دارد |
| محصولات با مشخصات | ۱۴۴٬۵۹۹ | مقایسه مشخصات دسته‌محور |
| فروشگاه با weekly_hours | ۴٬۴۷۳ | زمان مناسب مراجعه |
| دارای نشانه پاساژ | ۳٬۶۵۱ | استخراج mall/floor/unit با شواهد |
| فروشگاه دارای اعتبار حضوری | ۸۲ | فیلتر اعتباری با empty-state دقیق |
| آفر بدون قیمت | ۱۵٬۰۸۳ | سه‌حالته بودن قیمت |
| آفر بدون تاریخ آخرین تغییر | ۷۶۹ | اطلاعات نامشخص نه فرض تازه |

**قرارداد حقیقت:** `Product` مشخصات کالا، `Shop` کسب‌وکار/مکان/ساعات/گزینه‌های پرداخت، و `Offer` رابطه محصول و فروشگاه با قیمت و گارانتی است. فقط `Offer` اجازه نسبت‌دادن «این فروشگاه این کالا را آفر کرده» می‌دهد. سن آخرین تغییر قیمت معادل تأیید فعلی قیمت نیست. علامت «موجودی تأییدشده» فقط از نتیجه معتبر استعلام همان سناریو می‌آید.

**خط مشی کیفیت:** داده خام حفظ شود؛ normalize فقط در نمای جست‌وجو انجام شود. قیمت Decimal/Numeric در DB و رشته تومان در JSON است. فیلدهای تهی همیشه تمایز `unknown` دارند. قیمت‌های پرت در import حذف نشوند؛ سیاست نمایش آنها صریح و قابل تست باشد. مکان‌ها مختصات ورودی هستند؛ فاصله مستقیم با مسیر/زمان سفر متفاوت است.

## ۲. کاربران، Job-to-be-Done و جریان‌های کلیدی

**شخصیت A: جست‌وجوگر مردد.** «برای کارم یک لپ‌تاپ خوب می‌خواهم، مدل نمی‌دانم.» موفقیت: ۲ تا ۴ پیشنهاد با دلیل انتخاب و مشخصات مقایسه‌پذیر، نه پاسخ متنی طولانی.
**شخصیت B: خریدار دارای شرط.** «فقط تا ۳۰ میلیون، حضوری قسطی، نزدیک ونک.» موفقیت: عدم نقض هر شرط، توضیح شفاف در صورت نبود نتیجه.
**شخصیت C: آماده مراجعه.** «مدل دقیق را می‌دانم، امروز کجا بروم؟» موفقیت: کمترین کلیک تا فهرست فروشندگان، استعلام و کارت مراجعه.
**شخصیت D: خریدار در حالت شکست.** «فروشگاه انتخاب‌شده پاسخ نمی‌دهد.» موفقیت: حفظ تمام انتخاب‌ها و یافتن جایگزین بدون آغاز دوباره.

### ۲.۱ نقشه مأموریت (Mission Lifecycle)

`NEW → DISCOVERING → PRODUCT_SELECTED → EXPLORING_SHOPS → AWAITING_CONTACT_APPROVAL → VERIFYING → {VERIFIED | RECOVERY_NEEDED} → READY_TO_VISIT → COMPLETED`

شاخه‌های ثانویه: `NEEDS_CLARIFICATION`, `NO_MATCH`, `NO_ANSWER`, `UNAVAILABLE`, `PRICE_CHANGED`, `CLOSED`, `PROVIDER_ERROR`, `USER_CANCELED`. این‌ها باید state انتقال تعریف‌شده داشته باشند؛ تمام خطاها نباید به `FAILED` تبدیل شوند.

**اصول جریان:**
- آغاز از متن طبیعی یا انتخاب دسته؛ ورودی موقعیت اختیاری است.
- سؤال فقط درباره اطلاعات ضروریِ اثرگذار بر کیفیت نتیجه؛ پیشنهاد سؤال باید دکمه/انتخاب سریع داشته باشد.
- انتخاب مدل پس از مقایسه حداکثر ۳ محصول، مگر کاربر تعداد دیگری بخواهد.
- روی موبایل یک سطح اصلی در هر لحظه: کشف، مقایسه، فروشندگان، پیگیری یا مراجعه؛ همه مراحل قابل بازگشت باشند.
- پیش از هر اثر جانبیِ تماس، تأیید کاربر در صورت سیاست محصول درخواست شود و در state ثبت شود.
- پس از پاسخ ناموفق، گزینه‌های جایگزین تنها با حفظ تمام شروط سخت پیشنهاد شوند.

### ۲.۲ سناریوی طلایی داوری

ورودی نمونه مفهومی: «برای برنامه‌نویسی لپ‌تاپ تا ۵۰ میلیون می‌خواهم، ترجیحاً نزدیک ونک و اگر شد قسطی». جست‌وجوی واقعی فقط با داده‌های قابل استخراج از CSV انجام شود. نوع تقاضای «ترجیحاً» نرم است، «تا ۵۰ میلیون» سخت؛ «اگر شد قسطی» اولویت است، نه حذف همه غیرقسطی‌ها مگر تأیید شود.

1. فهم نیاز با summary مختصر در UI.
2. جست‌وجوی محصولات منطبق و مقایسه ۲ تا ۳ مدل بر اساس مشخصه واقعی موجود در CSV.
3. انتخاب مدل و نمایش فروشندگان با چیدمان list/map و فیلترهای فعال.
4. تغییر فیلتر خرید اعتباری و مشاهده اثر آن بر نتایج بدون prompt جدید.
5. انتخاب فروشگاه و تأیید «بررسی موجودی و قیمت».
6. بازگشت سناریوی `no_answer` از fixture سروری، نه پارامتر کلاینت.
7. پیشنهاد فروشنده پشتیبان مطابق شروط سخت.
8. نتیجه استعلام دوم و تولید کارت مستقل «آماده حرکت».
9. نمایش نام پاساژ/طبقه/واحد فقط اگر در داده باشد، آدرس و لینک نقشه.

**الزام دمو:** همه محصولات/فروشندگان دمو با IDهای داده اصلی در fixture مشخص و قابل‌بازتولید باشند. سناریوی نمونه تا پیش از import CSV نباید به‌عنوان دمو واقعی نمایش داده شود.

## ۳. معماری تجربه کاربری (Information Architecture)

### ۳.۱ صفحه شروع

Topbar کوچک با برند/مأموریت‌های اخیر؛ تیتر «چی می‌خوای بخری؟»؛ یک ورودی طبیعی بزرگ؛ سه پیشنهاد قابل‌انتخاب («کمک برای انتخاب»، «پیدا کردن مدل مشخص»، «خرید قسطی»). درخواست GPS قبل از ضرورت ممنوع. مکان پیش‌فرض «تهران / منطقه نامشخص» قابل تغییر است. شرح طولانی امکانات در home حذف شود.

### ۳.۲ صفحه کشف/نتایج محصول

کارت: تصویر با fallback، عنوان، برند/مدل در صورت موجود بودن، حداکثر ۲ تا ۳ مشخصه مرتبط، کمترین آفر **واجد شرایط** و timestamp آن، تعداد فروشنده منطبق، توضیح دلیل پیشنهاد. انتخاب چند کارت برای مقایسه. تغییر بودجه یا اولویت از chip/filter؛ حداقل یک ناحیه «چرا این پیشنهاد؟» مبتنی بر داده.

### ۳.۳ صفحه مقایسه

مقایسه mobile با کارت‌های افقی قابل مرور و برچسب ثابت معیارها؛ دسکتاپ جدول با ستون محصولات. AttributeRegistry دسته‌محور: نام استاندارد، واحد، formatter، score_direction (بالاتر/کمتر/کیفی)، unknown. برای ۳ تا ۵ دسته اول مجموعه معیار قابل‌تکیه ساخته شود؛ سایر دسته‌ها fallback به مشخصات خام ساختاریافته داشته باشند. ادعای «بهتر» فقط با دلیل مشخص و بدون اختراع مشخصات.

### ۳.۴ فروشندگان: Shop Explorer

ترتیب معیارها در کارت: نام فروشگاه، قیمت ثبت‌شده و زمان آخرین تغییر، روش پرداخت، فاصله مستقیم یا ETA با برچسب صحیح، ساعات کاری و نشانی کوتاه. فهرست و نقشه **یک state انتخاب واحد** دارند. نوار chips برای فیلترهای اعمال‌شده؛ Bottom Sheet فیلتر روی موبایل با دکمه «نمایش N نتیجه»؛ دکمه اقدام اصلی در جای ثابت. مقایسه فروشنده با کارت‌های قابل مقایسه (قیمت/راه/گارانتی/اعتباری/اطلاعات نامشخص).

### ۳.۵ پیگیری استعلام

پنل وضعیت تنها مراحل واقعاً انجام‌شده را نشان دهد: «در انتظار تأیید»، «در حال بررسی در سناریوی دمو»، «پاسخ دریافت شد»، «بدون پاسخ»، «پیشنهاد جایگزین». پاسخ‌های بازار شبیه‌سازی‌شده را نباید با تماس خارجی واقعی اشتباه گرفت؛ در نسخه داوری برچسب ظریف «استعلام شبیه‌سازی‌شده» در پنل وجود داشته باشد. انتخاب «پیگیری فروشنده بعدی» یک عمل واقعی و کنترل‌شده است؛ دکمه خروج یا توقف هم وجود داشته باشد.

### ۳.۶ کارت «آماده حرکت»

کالا/مدل انتخاب‌شده، فروشگاه اصلی و پشتیبان، قیمت ثبت‌شده و زمان آن، قیمت/موجودی/ساعات تأییدشده بر اساس پاسخ سناریو و زمان همان پاسخ، شرایط پرداخت، آدرس، پاساژ/طبقه/واحد (از متن منبع)، مبدأ و مسیر اگر حساب شده، زمان پیشنهادی مراجعه اگر ساعت کافی است، اقدامات کپی نشانی و باز کردن نقشه، یادداشت «کدام چیزها هنوز نامشخص‌اند». کارت به تنهایی قابل استفاده باشد، بدون خواندن چت.

### ۳.۷ قواعد برچسب‌گذاری و Copy فارسی

- `Offer.price_toman`: «قیمت ثبت‌شده: ... تومان»؛ `null`: «قیمت ثبت نشده».
- `last_price_changed_at`: «آخرین تغییر قیمت: ...»؛ از «به‌روز شده همین امروز» بدون timestamp مطمئن پرهیز شود.
- موجودی: «موجودی در استعلام تأیید شد» تنها برای verified outcome؛ سایر موارد «وضعیت موجودی نامشخص/ناموجود در سناریو».
- ساعت: «طبق ساعات ثبت‌شده باز است» در برابر «بازبودن برای مراجعه تأیید شد».
- مسیر: «فاصله مستقیم» تا route provider زمان واقعی مسیر ارائه دهد؛ در نبود مبدأ «موقعیت روی نقشه».
- `unknown` برای گارانتی یا شرط پرداخت هرگز به «ندارد» تبدیل نشود.
- پیام خطا باید همراه اقدام بعدی باشد: «اتصال نقشه برقرار نشد. فهرست فروشگاه‌ها همچنان در دسترس است».

### ۳.۸ معیارهای دسترس‌پذیری و RTL

`html lang="fa" dir="rtl"`; قلم مناسب فارسی مانند Vazirmatn با fallback؛ CSS logical properties؛ اعداد قیمت با `Intl.NumberFormat('fa-IR')`، اما مقدارهای مالی از decimal-string و بدون تبدیل خطرناک به Number؛ URL/شناسه و شماره مدل با `dir="ltr"` در محدوده خود. کیبورد، focus ring، aria-label، aria-live برای نتایج و dialogها، reduced-motion، contrast حداقل WCAG 2.2 AA، کنترل‌های اصلی لمس حدود ۴۴px و skeleton بدون حرکت شدید. portalهای dropdown/dialog باید RTL واقعی بگیرند. آزمون روی عرض‌های ۳۲۰، ۳۶۰، ۳۹۰، ۷۶۸ و ۱۴۴۰ پیکسل.

### ۳.۹ وضعیت‌های مشترک کامپوننت‌ها

`idle`, `loading`, `ready`, `empty`, `partial`, `stale`, `error_recoverable`, `error_blocked`, `offline`, `unknown`, `simulated_verification`, `confirmed`. هر endpoint پاسخ خطا با کد ثابت داشته باشد. برای loading نتایج فیلترها، محتوای قدیمی با علامت «در حال به‌روزرسانی» می‌تواند حفظ شود اما نباید نتیجه جدید معرفی گردد.

## ۴. طراحی فنی و ساختار مخزن

```
frontend/                       React 19 / TypeScript / Vite / TanStack Query
  src/app/                     entry, router/workspace, providers
  src/features/discovery/      search and product cards        [TARGET]
  src/features/comparison/     category-aware comparison       [TARGET]
  src/features/shops/          list/map/payment/visit hours    [TARGET]
  src/features/contact/        approvals and tracking         [TARGET]
  src/features/visit-plan/     ready-to-go summary            [TARGET]
  src/features/missions/       existing legacy implementation
  src/shared/                  API client, tokens, components
backend/                        Django / DRF
  apps/catalog/                Product, Shop, Offer, import
  apps/search/                 query interpretation, retrieval, filters
  apps/agent/                  LangGraph agent and simulation
  apps/missions/               mission, events, checkpoints, contacts
  apps/health/                 process and readiness
  apps/eligibility/            offer-level rule engine         [TARGET]
  apps/visit/                  hours, routes, itinerary       [TARGET]
docs/blueprint/                 normative delivery specification
reports/                        source audit snapshots; NOT dataset files
.github/workflows/              automated quality checks
```

`[TARGET]` یعنی هنوز در کد منتقل‌شده موجود نیست و باید ایجاد شود؛ نه نام فایل آماده اجرا. ساختار فعلی را یکباره به monorepo جدید با چند ابزار build انتقال ندهید. دامنه قابلیت‌ها از طریق سرویس/کامپوننت جدا شود. اصل Dependency Direction: API -> Application service -> Domain Policy -> Repository/Provider؛ Domain Policy وابسته به HTTP یا LLM نیست.

### ۴.۱ لایه مدل و داده

**اصلی:** `Product(source_id, persian_title, brand_name, category_name, model, specs, image_urls, normalized_title)`؛ `Shop(source_id, name, address, lat, lon, weekly_hours, payment_options, ...)`؛ `Offer(source_id, product_id, shop_id, price_toman, last_price_changed_at, seller_title, description, warranty)`.

**پیشنهاد توسعه:** `PurchaseMission(id, anonymous_access_hash, stage, status, constraints, preferences, state_version, revision, selected_product_id, selected_offer_id, created_at, updated_at)`؛ `MissionEvent(mission_id, seq, type, schema_version, payload, created_at)`؛ `ContactAttempt(id, mission_id, shop_id, offer_id, purpose, outcome, source_type, verified_price, verified_stock, verified_hours, scenario_version, idempotency_key, created_at)`؛ `VisitPlan(id, mission_id, snapshot_json, version, created_at)`؛ `ScenarioFixture(key, seed, outcomes, version)` برای محیط demo قابل کنترل.

از JSON برای فیلدهای کم‌تکرار و انعطاف‌پذیر استفاده شود؛ اطلاعات پرتکرار جست‌وجو با ستون/ایندکس مناسب. `OfferEligibility` در سطح آفر اجرا گردد و `credit` provider فقط وقتی واجد شرایط باشد که `channel=in_person`, `min_price_toman <= offer.price <= max_price_toman` و دسته محصول هم منطبق باشد؛ اگر متادیتای لازم تهی است نتیجه باید با سیاست سه‌حالته `eligible | ineligible | unknown` مدیریت شود.

### ۴.۲ مسیر import و داده

1. آدرس فایل‌های خام CSV از متغیر تنظیمات؛ فایل واقعی در git قرار نگیرد.
2. ثبت SHA-256 و `dataset_version` و تاریخ import.
3. validation schema و JSON fields، duplicate IDs، مختصات، تاریخ‌ها و decimal.
4. import قابل‌تکرار و idempotent با batch transactions؛ ابتدا Product/Shop سپس Offer، حفظ `source_id`.
5. کنترل cardinality، orphan FKs، تعداد nullها و درصد پارامترهای کسب‌وکار.
6. خروجی manifest و گزارش قابل مقایسه؛ readiness تا تکمیل import معتبر، موفق اعلام نشود.
7. عدم نمایش شماره‌های ساختگی در UI عمومی مگر سیاست رسمی مسابقه اجازه داده باشد؛ شبیه‌ساز از contact channel همان جهان شبیه‌سازی استفاده کند.

### ۴.۳ Retrieval، ranking و ranking explanation

**پیش‌پردازش فارسی:** یکسان‌سازی ي/ی، ك/ک، فاصله/نیم‌فاصله، ارقام فارسی و لاتین، نشانه‌گذاری، عبارت‌های چندکلمه‌ای، synonyms دسته/برند و aliasهای مدل. مقادیر نمایشی منبع تغییر نکند.

**ExtractIntent:** Pydantic schema شامل `entity`, `category`, `brand`, `model`, `use_case`, `hard_constraints`, `soft_preferences`, `confidence`, `clarification_question`؛ نبود مدل LLM باعث شکست جست‌وجوی صریح نباشد (deterministic parser fallback). پاسخ مدل برای هر hard constraint تنها «پیشنهاد ساختار» است و validator نهایی تصمیم می‌گیرد.

**Candidate Retrieval:** ترکیب exact model match، brand/category match، trigram similarity، match در عنوان و specs. ابتدا baseline lexical با PostgreSQL + `pg_trgm` و benchmark؛ pgvector تنها پس از اندازه‌گیری بهبود Recall@10/MRR@10. از OR ساده کلمات برای گرفتن نتیجه وادارشده به ارتباط خودداری شود؛ ضریب برند/مدل و phrase match با مجموعه golden ارزیابی شود.

**Eligibility:** اعمال همه شروط سخت در سمت سرور؛ بدون Offer واجد شرایط، Product در لیست «خریدنی» ظاهر نشود. unknown price با filter سقف بودجه واجد شرایط حساب نشود. credit به تفکیک `strict` و `preferred`، نزدیکی با radius `strict` یا distance ranking `preferred`. نبود نتایج سبب تغییر خودکار شرط نمی‌شود.

**Ranking پیشنهادی برای بازتنظیم تجربی (نه ادعای وزن بهینه):** ابتدا فیلتر سخت؛ سپس امتیاز ارتباط با نیاز + منطبق‌بودن با ترجیحات + کیفیت داده/گارانتی + رتبه قیمت و زمان سفر بر اساس ترجیح. normalization امتیازها فقط در گروه نتایج قابل مقایسه. هر reason کد و `evidence` داشته باشد: مثلاً `WITHIN_BUDGET:{offer_id,amount,cap}`؛ توضیح ساختگی مدل ممنوع. هیچ امتیاز اعتماد جادویی بدون مبنای داده نمایش داده نشود.

**No-result Diagnostic:** آمار جداگانه فیلترهای بازدارنده محاسبه شود و تغییرات پیشنهادشده با تخمین تعداد نتایج مستقل از هم نشان داده شوند؛ هیچ relaxation بدون عمل کاربر اجرا نشود. اگر پوشش منطقه نیست، ادعای «هیچ فروشگاهی در آن منطقه وجود ندارد» ممنوع؛ فقط «در داده فعلی گزینه منطبقی پیدا نشد».

### ۴.۴ Geo و زمان مراجعه

نقشه: `@neshan-maps-platform/maplibre-sdk` در صورت دسترسی و شرایط مجوز؛ SDK قابل تعویض پشت `MapProvider`. سرویس Route/Matrix به‌صورت backend proxy با key سروری و کنترل quota. برای shortlist: Haversine روی WGS84 → top K → Matrix ETA و sort بر اساس زمان واقعی؛ در نبود سرویس، فقط فاصله مستقیم با برچسب. مبدأ کاربر فقط هنگام نیاز درخواست شود و بدون consent در لاگ دائمی قرار نگیرد.

`VisitHoursService` باید روزهای هفته تهران (Asia/Tehran)، شیفت‌های چندگانه، شیفت عبوری از نیمه‌شب، `closed`, `unsupported`, `unknown` و timezone را تفسیر کند. `open_now_declared` و `open_at_eta_declared` دو چیز متفاوت‌اند. ETA ترافیکی باید زمان صدور/TTL داشته باشد؛ بدون ETA، زمان رسیدن تخمین زده نشود.

`AddressHintExtractor`: parse نام پاساژ، طبقه، واحد، نشانه مکانی از `Shop.address/location_label` و حفظ text provenance؛ confidence فقط کیفیت استخراج را نشان دهد نه GPS داخل پاساژ. در نبود متن، نمایش «جزئیات طبقه/واحد ثبت نشده».

## ۵. معماری Agent و تماس با فروشنده

### ۵.۱ مرز هوش مصنوعی

LLM می‌تواند intent را به schema تبدیل کند، سؤال تکمیلی کوتاه پیشنهاد دهد، مقایسه مشخصات را پس از normalization توضیح دهد و مرحله بعد را از ابزارهای allowlist انتخاب کند. LLM نباید: SQL خام/URL دلخواه اجرا کند، بدون مجوز با فروشنده تماس بگیرد، قیمت/موجودی اختراع کند، شرط سخت را حذف کند، HTML/JS قابل اجرا تولید کند یا خروجی ابزار را به‌عنوان دستور سیستم تلقی کند.

### ۵.۲ State پیشنهادی

```
MissionGraphState = {
  mission_id, thread_id, revision, stage, user_intent,
  hard_constraints, soft_preferences, clarifications,
  candidate_product_ids, selected_product_id,
  eligible_offer_ids, selected_offer_id, backup_offer_ids,
  approval_state, pending_action, contact_attempt_ids,
  verification_result, visit_plan_id, last_error,
  telemetry_correlation_id
}
```

پیام‌های تاریخچه محدود و data ID-based ذخیره شوند؛ فهرست کامل نتایج یا متن خام دیتاست در checkpoint کپی نشود.

### ۵.۳ LangGraph گراف پیشنهادی

```
START → interpret → need_clarification?
             ├ YES → pause_for_user → interpret
             └ NO  → retrieve_products → validate_eligibility → present_products
                                      → pause_for_product_select
                                      → shortlist_shops → present_shops
                                      → pause_for_contact_approval
                                      → execute_contact → evaluate_result
                                           ├ available → build_visit_plan → READY
                                           ├ no_answer → alternate_shop → approval/check
                                           ├ unavailable → alternate_shop/product → approval/check
                                           ├ price_changed → revalidate_constraints → approval/check
                                           ├ closed → reconsider_time/shop → approval/check
                                           └ error → retry_policy/fallback → WAITING
```

قرار نیست فیلترهای UI هر بار گراف را اجرا کنند: درخواست‌های synchronous و deterministic مستقیم به `/catalog/search` یا `/offers` می‌روند و فقط state نسخه‌دار مأموریت را به‌روز می‌کنند. `interrupt` برای تأییدها و PostgreSQL checkpointer برای بازیابی durable استفاده شود. پیش از node قابل replay هیچ side effect بدون idempotency رخ ندهد؛ در LangGraph از re-execution node هنگام resume باید آگاه بود.

### ۵.۴ ContactProvider و سناریو

```
ContactProvider.verify(
 mission_id, offer_id, purpose, approved_action_id, idempotency_key
) -> ContactResult
```

`ContactResult` شامل `outcome`, `source=demo_simulation`, `observed_at`, `stock_status`, `confirmed_price_toman?`, `hours_response?`, `message`, `scenario_key`, `scenario_version`, `attempt_id` باشد. سه purpose مستقل: `verify_stock`, `verify_price`, `verify_hours`، و حالت ترکیبی اگر نیاز محصول اقتضا کرد. `no_answer`, `unavailable`, `closed`, `price_changed`, `confirmed`, `error` را پوشش دهد. فقط سرور fixture و seed را انتخاب کند. اقدام تکراری با کلید یکسان باید همان `ContactAttempt` را برگرداند. outcome با زمان و shop و offer پیوند داشته باشد.

**ریسک مدل قبلی:** شبیه‌ساز نمونه فعلی فقط verify_availability را اجرا می‌کند و انتخاب outcome به چرخه attempt وابسته است. این باید جایگزین شود، نه روی UI تزئینی پنهان گردد.

### ۵.۵ سیاست بازیابی

- `no_answer`: از top K فروشنده دیگر که همان Product را با همه شروط سخت دارد، گزینه بعدی پیشنهاد شود؛ تعداد تلاش محدود (مثلاً ۳، قابل تنظیم) و بدون تماس نامحدود.
- `unavailable`: اول همان Product نزد فروشنده دیگر؛ اگر نشد، محصول جایگزین از matching specs با **تأیید کاربر**.
- `price_changed`: قیمت تأییدشده با budget بررسی شود؛ اگر فراتر رفت، با توضیح و اجازه کاربر جایگزین.
- `closed`: ساعت آینده از داده/استعلام؛ فقط اگر قابل‌محاسبه بود؛ وگرنه فروشگاه دیگر.
- `provider_error`: اعلام «امکان بررسی فعلاً در دسترس نیست»، retry با backoff محدود و ادامه با اطلاعات ثبت‌شده به عنوان unverified.

هر خروجی ایجنت باید `reason_codes`, `evidence_refs`, `next_actions` داشته باشد. خلاصه دلیل کاربرپسند قابل نمایش است؛ زنجیره تفکر خصوصی مدل نشان داده نشود.

## ۶. قرارداد API v1.1 پیشنهادی

**وضعیت:** این قرارداد هدف است؛ همه endpointها در baseline پیاده نشده‌اند. در `docs/api-contract.fa.md` قرارداد قدیمی وجود دارد، اما این بخش برای توسعه جدید مرجع تصمیم است.

اصول: prefix `/api/v1/`; response JSON UTF-8؛ ISO-8601 UTC؛ قیمت به string صحیح تومان؛ شناسه‌های source به string؛ خطا `{error:{code,message,details?,request_id}}`؛ pagination `page`, `page_size<=50`؛ `X-Request-ID`؛ در mutation `Idempotency-Key`؛ `ETag` یا revision در update state؛ structured error برای dependency down؛ queryهای متنی حداکثر ۲۰۰ نویسه؛ client input validate در DRF و schema domain.

| Method | Endpoint | خروجی/عملکرد | وضعیت فعلی |
|---|---|---|---|
| GET | `/api/v1/health/live/` | زنده‌بودن پروسه | baseline |
| GET | `/api/v1/health/ready/` | DB + schema + dataset version | نیازمند تکمیل |
| GET | `/api/v1/catalog/search/` | products+best offer+facets+reasons | baseline، اصلاح retrieval |
| GET | `/api/v1/products/{id}/` | محصول/مشخصات | baseline |
| GET | `/api/v1/products/{id}/offers/` | آفرها/گارانتی/credit eligibility/geo | baseline، تکمیل DTO |
| GET | `/api/v1/shops/{id}/` | فروشگاه، آدرس، ساعات، روش پرداخت | baseline |
| POST | `/api/v1/missions/` | مأموریت با درخواست اولیه | baseline، نسخه‌دارسازی |
| GET | `/api/v1/missions/{id}/` | snapshot و actions مجاز | baseline، تکمیل |
| PATCH | `/api/v1/missions/{id}/constraints/` | اعمال شروط با revision | هدف |
| POST | `/api/v1/missions/{id}/selections/` | انتخاب محصول یا آفر | هدف |
| POST | `/api/v1/missions/{id}/actions/` | approve/reject/resume graph | هدف |
| POST | `/api/v1/missions/{id}/contact-attempts/` | استعلام کنترل‌شده/idempotent | baseline محدود، توسعه |
| GET | `/api/v1/missions/{id}/events/?after_seq=N` | رویدادهای قابل بازیابی SSE | هدف |
| GET | `/api/v1/missions/{id}/visit-plan/` | کارت مستقل برنامه مراجعه | هدف |
| POST | `/api/v1/route-matrix/` | top K ETA از provider و fallback | هدف |

### ۶.۱ قرارداد پاسخ شفاف آفر (نمونه ساختاری؛ داده ساختگی به‌عنوان مثال)

```json
{
  "offer_id":"offer_example",
  "product_id":"product_example",
  "shop_id":"shop_example",
  "recorded_price_toman":"24900000",
  "last_price_changed_at":"2026-10-13T00:02:35Z",
  "registered_offer_is_stock_confirmation":false,
  "warranty":{"known":false,"details":null},
  "credit":{"status":"unknown","providers":[]},
  "verification":{"source":"not_checked","stock":"unknown","price":null,"observed_at":null},
  "distance":{"kind":"straight_line","meters":null},
  "route":{"status":"not_requested","eta_seconds":null}
}
```

### ۶.۲ رویدادها و رفتار reconnect

Schema version شده: `mission.created`, `intent.parsed`, `search.started`, `search.completed`, `selection.changed`, `approval.required`, `contact.started`, `contact.completed`, `alternatives.ready`, `visit_plan.ready`, `mission.failed`. همه رویدادها دارای `mission_id`, `seq`, `schema_version`, `emitted_at`, `payload` هستند. SSE از event log پایدار خوانده شود؛ `Last-Event-ID` یا `after_seq` امکان replay دارد. UI اگر نتوانست به stream وصل شود snapshot polling انجام دهد. هیچ مرحله progress نمایشی جایگزین اجرای واقعی نشود.

### ۶.۳ کنترل سطح دسترسی

در نسخه بدون حساب: شناسه مأموریت به‌تنهایی راز دسترسی محسوب نشود؛ token مالکیت تصادفی در cookie امن HttpOnly یا هدر session و hash ذخیره‌شده سرور استفاده شود. CSRF/CORS مشخص، rate limit بر اساس IP/session، idempotency و input caps. درخواست انتخاب offer باید دوباره در سرور با constraints بررسی شود. از log کامل مکان/محتوای پیام و keys provider پرهیز شود.

## ۷. Design System و ساختار کامپوننت

پالت پیشنهادی مبتنی بر سبز تیره کاربردی؛ سایر رنگ‌ها از neutral scale؛ semantic tokens `--bg`, `--surface`, `--surface-muted`, `--text`, `--text-muted`, `--border`, `--brand`, `--success`, `--warning`, `--danger`, `--focus`. نسخه تاریک اختیاری و پس از light-quality؛ رنگ نباید تنها حامل وضعیت باشد. spacing پایه ۴px؛ radius ثابت ۸/۱۲/۱۶؛ ارتفاع target کنترل‌های اصلی حداقل حدود ۴۴px. typography فارسی با تنظیم line-height ~1.65 برای متن و 1.35 برای تیتر؛ اعداد و برچسب قیمت در اندازه متناسب.

**Components طراحی مورد نیاز:** `SearchComposer`, `QuickIntentChips`, `ActiveFilterChips`, `ProductCard`, `ComparisonMatrix`, `ShopListCard`, `MapCanvas`, `ShopDetailsSheet`, `CreditEligibilityBadge` (فقط status meaningful), `ContactApprovalCard`, `VerificationTimeline`, `AlternativeChoiceCard`, `VisitPlanCard`, `ConfidenceEvidence`, `EmptyStateWithRecovery`, `ErrorBoundary`, `ResultSkeleton`.

**State Ownership:** URL/query params برای فیلترهای اشتراک‌پذیر؛ TanStack Query برای server/cache؛ component state برای sheet/open؛ mission snapshot در backend؛ agent checkpoint در backend؛ UI نباید رونویسی مجزای قیمت، موجودی یا offer eligibility داشته باشد. تغییر فیلتر یک request قابل لغو با `AbortSignal` است؛ نسخه‌های پاسخ قدیمی نباید روی پاسخ جدید overwrite کنند. هنگام تغییر بودجه اگر فروشگاه منتخب دیگر واجد شرایط نبود انتخاب در UI invalid شود و reason نشان داده شود.

**حفاظت تجربه:** حداکثر یک primary CTA برای هر card/مرحله؛ rich cards فقط در زمان نیاز؛ جلوگیری از شلوغی اولیه؛ skeleton واقعی، loading قابل لغو و پیام‌های خطای قابل‌فهم. تمام actionهای button رفتار قابل تست داشته باشند؛ UI تزئینی بدون عملکرد در نسخه داوری ممنوع.

## ۸. امنیت، محرمانگی و کیفیت عملیاتی

- `.env`, tokens, secrets, DB dumps, user coordinates, raw private files, `node_modules`, `.venv`, build artifacts را وارد git نکنید؛ `.env.example` فقط placeholder.
- هر credential احتمالی که در آرشیو قبلی بوده باید پیش از استفاده عمومی rotate شود؛ بدون مشاهده مقدار محرمانه، امن بودنش فرض نمی‌شود.
- prompt injection در توضیحات محصول یا وب‌سایت نباید بتواند ابزارها را هدایت کند. داده فروشنده untrusted content است، نه instruction. مسیر ابزارها allowlist شود.
- server-side hard constraints، validation، serialization امن، sanitization متن، CSP مناسب، CORS محدود، session ownership و CSRF بررسی شود.
- external API (map/LLM) دارای timeout، retry محدود، cache، circuit-breaker ساده و typed fallback باشد؛ log فقط correlation ID و status/code و latency.
- readiness: اتصال DB + migrations + شمارش/نسخه dataset + توان یک query نمونه؛ liveness جدا. backup و migration rollback در runbook.
- لاگ مأموریت شامل stage، revision، error code، elapsed_ms، tool name و ID مرجع باشد؛ متن خصوصی کامل را به‌طور پیش‌فرض ذخیره نکند. metricها: search latency p50/p95، contact success/failure distribution، mission completion، retry، no-result rate، map failures.

## ۹. ارزیابی: کیفیت واقعی پیش از دمو

### ۹.۱ Golden Set

حداقل ۵۰ پرسش مبتنی بر واقعی‌ترین نمونه‌های دیتاست: ۱۰ جست‌وجوی مدل دقیق، ۱۰ درخواست کاربردمحور، ۱۰ برند/مدل/فیلتر، ۵ قسطی، ۵ مکان، ۵ بدون نتیجه، ۵ typo/فارسی متفاوت. ground truth انسانی برای top relevant product IDs. دقت را با `Recall@10`, `MRR@10`, `nDCG@10` و نرخ نقض hard constraints (هدف **صفر**) بسنجید. baseline OR-token موجود و retrieval جدید را side-by-side اجرا کنید؛ vector search فقط در صورت بهبود پایدار.

### ۹.۲ سناریوهای E2E (حداقل ۱۲)

| ID | سناریو | معیار پذیرش |
|---|---|---|
| E01 | مدل مشخص و چند فروشنده | Offer/Shop ID معتبر و قیمت با unit |
| E02 | مدل نامشخص و کاربرد | سؤال ضروری یا پیشنهادهای قابل‌مقایسه |
| E03 | بودجه سخت | هیچ آفر فراتر از سقف پیشنهاد نشود |
| E04 | پرداخت اعتباری حضوری | provider/category/min/max صحیح |
| E05 | zero results | دلیل و تغییر شرط با اجازه کاربر |
| E06 | رد GPS | انتخاب دستی محدوده، ادامه کار |
| E07 | فقدان قیمت | unknown و پیشنهاد استعلام |
| E08 | فروشنده no answer | پیشنهاد جایگزین با شروط حفظ‌شده |
| E09 | تغییر قیمت | بازاعتبارسنجی بودجه، approval |
| E10 | فروشگاه بسته/ساعات نامشخص | ساعت ثبت‌شده/نامشخص جدا |
| E11 | پاساژ طبقه واحد | نمایش فقط داده استخراج‌شده |
| E12 | reconnect/duplicate contact | یک attempt واقعی، بازیابی stream |
| E13 | map API failure | fallback فهرست و نشانی |
| E14 | reload mid-mission | snapshot و تصمیم‌های قبلی حفظ شود |

### ۹.۳ Performance و دسترس‌پذیری

اهداف پیشنهادی، نه ادعای تست‌گذرانده: benchmark p95 جست‌وجو روی dataset واردشده؛ بودجه اولیه پیشنهادی p95 < ۱٫۵ ثانیه (نیازمند اندازه‌گیری)، TTI/UX روی شبکه throttled؛ Core Web Vitals در صدک ۷۵: LCP<=2.5s, INP<=200ms, CLS<=0.1. axe automated + keyboard/screen reader/manual فارسی؛ پشتیبانی `prefers-reduced-motion`. گرفتن ۱۰ بازخورد واقعی روی مأموریت، اندازه‌گیری success rate/time-to-plan و بررسی مشکل‌های کاربر بدون توضیح راهنما.

### ۹.۴ Quality Gates و Definition of Done

- Typecheck, lint, unit, backend pytest, migrations check, frontend build سبز.
- Import real dataset و integrity report ثبت‌شده؛ هیچ رکورد orphan.
- API contract test + simulator deterministic unit + graph recovery integration.
- تمام E01..E14 با داده fixture یا محیط integrated قابل اجرا و سبز.
- responsive + RTL + keyboard QA و mobile touch target.
- deployed HTTPS URL و health/readiness + demo scenario + screenshots.
- هیچ ادعای تماس خارجی، موجودی تأییدشده یا ETA بدون داده مرتبط.
- ۵ دقیقه ویدئوی دمو با صدای معرفی و عملکرد قابل مشاهده.

## ۱۰. نقشه اجرا و تقسیم کار

**نکته:** زمان‌ها در این سند برآورد تعهدشده نیستند؛ ترتیب وابستگی و خروجی‌ها معیار حرکت‌اند.

| فاز | کارهای وابسته | تحویل قابل بررسی | Gate |
|---|---|---|---|
| F0: Baseline/Repo | sanitization, git, CI, import check, deployment skeleton | اجرای محلی و smoke | health+data+lint |
| F1: Domain & Retrieval | schemas, normalize, eligibility, API DTO, search benchmark | query درست/فیلتر سخت | ۰ نقض شروط |
| F2: UX Core | IA, design tokens, home, result, compare, mobile | تجربه بدون چت اجباری | سناریوهای E01-E07 |
| F3: Shop & Geo | list/map, hours, credit, address hints, route provider | فروشندگان قابل مقایسه | E04/E06/E10/E11/E13 |
| F4: Mission Agent | persisted graph, approval, contact, recover, events | recovery قابل‌تکرار | E08/E09/E12/E14 |
| F5: Visit Plan & Polish | plan card, a11y, performance, testing | آماده مراجعه | سناریوی طلایی |
| F6: Deploy & Demo | release hardening, monitoring, demo rehearsal | نسخه آنلاین + فیلم | داوری |

**قانون تغییر:** هیچ قابلیت P1 تا زمانی که F0-F4 و golden path پایدار نشده‌اند به هسته اضافه نشود. اثر هر تغییر UX با تست نسخه موبایل و سناریوهای پذیرفته‌شده بررسی شود.

### ۱۰.۱ بک‌لاگ اولویت‌دار با تعریف پذیرش

- [P0] ثبت dataset version/checksum و verification readiness؛ acceptance: import دو بار نتیجه همسان و orphan=0.
- [P0] OfferEligibility در سطح provider؛ acceptance: min/max/category/channel tests سبز.
- [P0] سرچ با exact model + normalized Persian + comparator؛ acceptance: بهبود golden metrics نسبت به baseline و hard violations صفر.
- [P0] API DTO complete price/warranty; acceptance: missing ≠ false و ISO timestamp.
- [P0] RTL DesignSystem و جداسازی MissionPanel؛ acceptance: screenshots/mobile/keyboard.
- [P0] Map/List shared state + fallback؛ acceptance: انتخاب pin/card دوطرفه.
- [P0] Contact simulator server-side deterministic + price/hours; acceptance: replay همان outcome برای همان key.
- [P0] Postgres checkpointer/approval/recovery; acceptance: reload/retry سالم و duplicate صفر.
- [P0] VisitPlan مستقل؛ acceptance: قابل بازیابی بدون transcript.
- [P0] CI, deploy, ۵ دقیقه دمو؛ acceptance: smoke روی URL نهایی.
- [P1] multi-item route optimization فقط پس از کیفیت موجود.
- [P2] vision search/pgvector فقط پس از benchmarks و پوشش datasets.

## ۱۱. دمو پنج‌دقیقه‌ای و اسکریپت ضبط

- ۰۰:۰۰–۰۰:۳۵: مسئله انسانی و ورودی نیاز طبیعی.
- ۰۰:۳۵–۰۱:۱۵: مقایسه مدل‌ها و دلایل قابل استناد.
- ۰۱:۱۵–۰۲:۰۰: نقشه+لیست، تغییر بودجه/اعتباری/محدوده و اثر فوری.
- ۰۲:۰۰–۰۳:۰۰: استعلام سناریویی پس از approval؛ نمایش عدم پاسخ.
- ۰۳:۰۰–۰۴:۰۰: بازیابی خودکار و پیشنهاد فروشگاه پشتیبان.
- ۰۴:۰۰–۰۵:۰۰: کارت آماده حرکت با نشانی داخل پاساژ، وضعیت داده‌ها و مسیر.

کل دمو روی نسخه deploy شده انجام شود. داده‌های نمونه و outcomeها با script fixture سمت سرور و seed مشخص آماده شوند. متن‌خوانی خالی و نمایش سورس کد به‌جای تجربه کاربر نباشد. اگر API خارجی در دسترس نبود باید fallback معنادار نشان داده شود، نه mock ETA ساختگی.

## ۱۲. ریسک‌ها، تصمیم‌های باز و سیاست رفع ابهام

| ریسک/ابهام | سطح | اقدام عملی |
|---|---|---|
| CSV خام داخل آرشیو نیست | بحرانی | دریافت مجموعه اصلی و audit مجدد؛ fixtureهای واقعی از CSV |
| صحت import/PostgreSQL runtime تأیید نشده | بحرانی | local compose, migrate, import, test |
| کلید SDK نشان و quota مشخص نیست | بالا | provider contract + test Tehran + fallback list |
| کیفیت LLM ناشناخته است | بالا | golden intents + heuristic fallback + trace sampling |
| استعلام واقعی از شماره‌های ساختگی ممکن نیست | دامنه چالش | شبیه‌ساز سروری با provenance روشن و قابل تعویض |
| زمان سفر بدون API تخمین‌ناپذیر است | بالا | برچسب direct-distance، Matrix فقط پس از provider |
| محتوای specs بسیار ناهمگون است | متوسط | ۳–۵ دسته منتخب + raw specs fallback |
| دیتاست پوشش کامل تهران نیست | متوسط | copy «در داده موجود»، نه «در تهران نیست» |
| تیم/زمان/بودجه پروژه مشخص نیست | مدیریتی | gate-based scope و قفل P0 قبل از P1 |
| لایسنس مخزن مشخص نیست | حقوقی | فعلاً LICENSE عمومی قرار داده نشود؛ مالک کد تصمیم بگیرد |
| اطلاعات در .env قدیمی بوده است | امنیتی | عدم انتشار، rotate در صورت واقعی بودن |

**Decision Log:** ADRهای فعلی پروژه صرفاً تاریخچه‌اند. این سند و acceptance tests مرجع هدف هستند. تصمیم‌های جدید نسخه‌دار در `docs/blueprint/DECISIONS.fa.md` ثبت شوند و هر خروج از طرح با evidence/benchmark تأیید شود.

## ۱۳. پژوهش و نمونه‌های متن‌باز به‌عنوان مرجع الگویی

- Google Shopping / Let Google Call: https://blog.google/products/shopping/google-shopping-ai-updates-2025/ (الگوی پیگیری خرید محلی؛ انتشار/دسترسی هر قابلیت را در منطقه خودمان فرض نکنید)
- CopilotKit travel example (shared agent state + map + HITL): https://github.com/CopilotKit/CopilotKit/tree/main/examples/v1/travel
- CopilotKit Travel `use-trips.tsx`: https://github.com/CopilotKit/CopilotKit/blob/main/examples/v1/travel/lib/hooks/use-trips.tsx
- assistant-ui (conversation/tool UI): https://github.com/assistant-ui/assistant-ui
- Open Intelligent UI (controlled generative UI inspiration): https://github.com/CopilotKit/OpenIntelligentUI
- LangGraph agent chat UI: https://github.com/langchain-ai/agent-chat-ui
- LangGraph checkpoints: https://docs.langchain.com/oss/python/langgraph/persistence
- LangGraph interrupts: https://docs.langchain.com/oss/python/langgraph/interrupts
- shadcn RTL/Vite: https://ui.shadcn.com/docs/rtl/vite
- Neshan MapLibre SDK: https://platform.neshan.org/docs/sdk/web/maplibre/neshan-maplibre-gl-js/
- Neshan Matrix: https://platform.neshan.org/docs/api/routing-category/distance-matrix/
- PostgreSQL pg_trgm: https://www.postgresql.org/docs/current/pgtrgm.html
- Web Content Accessibility WCAG 2.2: https://www.w3.org/TR/WCAG22/
- OWASP Top 10 for LLM 2025: https://genai.owasp.org/llm-top-10/
- GitHub REST create repo: https://docs.github.com/en/rest/repos/repos#create-a-repository-for-the-authenticated-user

این منابع الگو و راهنمای پیاده‌سازی هستند، نه تضمین سازگاری نسخه‌های وابستگی یا صحت اجرا روی حساب/سرور پروژه. در زمان نصب و انتشار باید نسخه دقیق وابستگی و شرایط استفاده بررسی شوند.

## ۱۴. تعریف موفقیت نهایی

یک داور بتواند بدون راهنمایی توسعه‌دهنده در نسخه آنلاین نیاز خرید را مطرح کند، کالای مناسب را انتخاب و مقایسه کند، فروشگاه منطبق را روی نقشه/فهرست بیابد، شرایط پرداخت و ساعت را بفهمد، یک استعلام شبیه‌سازی‌شده واقعیِ پروژه را طی کند، در شکست اول از مسیر خارج نشود و برنامه مراجعه‌ای مستقل دریافت کند. تمام ادعاهای قیمت/موجودی/مسیر بر شواهد ابزار یا CSV متکی باشند؛ هیچ الزام تحویل یا UX بحرانی حذف نشده باشد.
