# تصمیم فنی React/OpenLayers نشان برای بازارکامپس | ۲۳ اکتبر ۲۰۲۶

**وضعیت:** تحقیق و نقشه اجرا کامل شده؛ **نصب SDK و نمایش واقعی نقشه نشان هنوز انجام نشده است**. نسخه current `main@20b3a110df95` دارای React 19.3.1، Vite و TypeScript است. صفحهٔ رسمی مورد درخواست مالک: https://platform.neshan.org/docs/sdk/web/openlayers/react-openlayers/ .

## نتیجه بررسی مستندات رسمی

- سند نشان نسخه آخر React OpenLayers را برای **React >=19.2.1** معرفی می‌کند. نسخه پروژه 19.3.1 با شرط اعلام‌شده سازگار است، ولی بدون نصب و اجرای Chromium سازگاری عملی **تأیید نشده**.
- `frontend/.npmrc` اکنون scope رجیستری رسمی نشان را با `@neshan-maps-platform:registry=https://npm.neshan.org` تنظیم می‌کند؛ **هیچ پکیج جدیدی هنوز به package.json/lock اضافه نشده**. نصب بعد از تأیید دسترسی CI/هاست: `cd frontend && npm install @neshan-maps-platform/react-openlayers @neshan-maps-platform/ol` همراه با commit هر دو فایل manifest و lock؛ import رسمی CSS: `@neshan-maps-platform/react-openlayers/dist/style.css`.
- کامپوننت `<NeshanMap mapKey={PUBLIC_WEB_MAP_KEY} center={{latitude:35.7,longitude:51.4}} zoom={13} poi={false} onInit={...} />`. **center الزامی در پیاده‌سازی ماست:** سند رسمی می‌گوید فقدان center ممکن است درخواست geolocation مرورگر را به‌صورت خودکار آغاز کند؛ چنین درخواستی بدون اقدام صریح کاربر غیرمجاز است.
- `onInit` نقشه `olMap` را به کد می‌دهد. برای markers باید از آبجکت‌های `@neshan-maps-platform/ol`، Vector Layer و Feature و تبدیل WGS84 `[lon,lat]` به projection نقشه استفاده شود. API شکل دقیق exports و typeها باید با نسخه package نصب‌شده و نمونه رسمی verify شود، نه با نوشتن import حدسی.
- کلید `mapKey` **کلید وب SDK** و به صورت محدود به دامنه عمومی است؛ کلید فعلی کاربر برای دو REST API مسیریابی و ماتریس کلید وب محسوب نمی‌شود. **REST key هرگز وارد frontend و `VITE_*` یا تاریخچه Git نمی‌شود.**
- logo/copyright و terms نشان باید روی نقشه باقی بمانند. map load تنها بعد از opt-in کاربر و قابلیت HTML list fallback. markup JSX بی‌کلید نباید خطا بدهد یا ناخواسته Location Permission prompt بدهد.

## قرارداد طراحی map/list

1. نقشه مشترک در `SellerLocationBoard` فقط هنگام انتخاب کاربر mount می‌شود؛ پیش‌فرض فهرست.
2. Points فقط برای `eligible_offers` جاری از همان `result_set_id` و سقف ۲۴ آفرِ بارگذاری‌شده هستند؛ dedupe by shop.id؛ نه جست‌وجوی نام‌های synthetic در نشان.
3. marker click و list click هر دو به `mission_focus({action:'select_offer',offer_id,result_set_id})` وصل می‌شوند. selected id فقط server-authoritative؛ pinned marker منسوخ action ندارد.
4. روشن بودن Web SDK هیچ اثری بر `NESHAN_ROUTING_ENABLED` و `NESHAN_DIRECTION_ENABLED` ندارد. محاسبه با ترافیک فقط با POST صریح و سقف سروری انجام می‌شود؛ فاصله مستقیم هیچ‌وقت ETA نیست.
5. با خطای tile/401/403/CORS، WebGL و شبکه، نقشه از دید مخفی می‌شود و لیست/نشانی/لینک رسمی نشان قابل استفاده باقی می‌مانند.
6. رنگ و status محصول نباید `available_verified` تلقی شوند؛ نام بیشتر فروشگاه‌ها و همه شماره‌ها synthetic هستند.

## پیش‌شرط توسعه نهایی (نیازمند مالک)

- [ ] آیا در [پنل نشان](https://platform.neshan.org/panel/login) **کلید وبِ مجزا برای Map SDK** ساخته شده؟ *صرف ساخت کلید RESTِ ماتریس و Direction کافی نیست.*
- [ ] دامنه وب **HTTPS واقعی** و domain allowlist برای وب‌کلید تعیین و تست شده؟ key raw ارسال نشود.
- [ ] دسترسی `npm.neshan.org` از GitHub Actions/هاست با نصب دقیق و lockfile قابل بازتولید تأیید شده؟ تا آن زمان **package.json/lock را عمداً دستکاری نکرده‌ایم** تا CI `npm ci` خراب نشود.
- [ ] هزینه tile/session و quota account نشان تأیید شده؟ بازشدن نقشه نباید بدون سقف مجاز باعث خرج ناخواسته شود.
- [ ] smoke واقعی دو REST (Matrix + Direction) از **هاست مقصد** با اجازه پرداخت انجام شده و 480/481/482/483/484/485 ندارد؟
- [ ] تست مدل marker OL با نمونه رسمی، React 19.3، RTL و 320/390/1440، browser back/forward، map cleanup و denied geolocation.

**کار جدید این PR:** فقط مسیر Direction با ترافیک به adapter backend و UI فعلی افزوده شده است؛ Web SDK map هنوز فعال و نصب نشده، و دلیلی برای وانمود کردن «نقشه چندپینِ نشان» وجود ندارد.

## منابع
- SDK React OpenLayers نشان: https://platform.neshan.org/docs/sdk/web/openlayers/react-openlayers/
- ماتریس با ترافیک: https://platform.neshan.org/docs/api/routing-category/distance-matrix/
- مسیر با ترافیک: https://platform.neshan.org/docs/api/routing-category/routing/
- راهنمای مالک: [NESHAN-OWNER-ACTION-GUIDE-2026-10-23.fa.md](NESHAN-OWNER-ACTION-GUIDE-2026-10-23.fa.md)
