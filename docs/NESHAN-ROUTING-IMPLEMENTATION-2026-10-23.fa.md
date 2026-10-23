# اجرای مرحله نخست اتصال نشان: آداپتور ایمن و کنترل‌شده ETA | ۲۳ اکتبر ۲۰۲۶

**وضعیت به‌روز بعد از PR #30:** آداپتور کنترل‌شده Matrix روی `main@fa06512839e9` ادغام شده و CI ۵/۵ موفق بوده است. **اتصال پرداختی به‌صورت پیش‌فرض خاموش است** و بدون کلید و quota معتبر ETA واقعی نمایش داده نمی‌شود. مرحله بعد: [راهنمای عملیاتی مالک](NESHAN-OWNER-ACTION-GUIDE-2026-10-23.fa.md) و لینک‌های بدون کلید نقطه/مسیر در نشان.

## قرارداد اجرایی
- `GET /api/v1/missions/{uuid}/route-estimates/`: فقط در نشست صاحب مأموریت؛ `{provider:"neshan",enabled:boolean,modes:[]}`، **هیچ فراخوانی نشان انجام نمی‌دهد**.
- `POST /api/v1/missions/{uuid}/route-estimates/`: `{result_set_id,origin:{lat,lon,source:"manual_region"|"geolocation_opt_in"},offer_ids:[1..5],mode:"car"|"motorcycle"}`. تمام offerها باید در فهرست فعلی فروشندگانِ محصول منتخب باشند، با شروط hard و مقصد معتبر تهران. مختصات مقصد از Shop دیتابیس حل می‌شود. origin دستی باید با مبدأ مأموریت مطابقت داشته باشد. duplicate offer و duplicate shop رد می‌شوند.
- حالت غیرفعال، بودجه تمام‌شده، خطای سهمیه/کلید، timeout، پاسخ نامعتبر، `NoRoute` هیچ زمان سفر ساختگی برنمی‌گرداند؛ فقط `status=unavailable` یا `no_route`.
- ارائه‌دهنده فقط به `https://api.neshan.org/v1/distance-matrix` با `Api-Key` سروری و HTTPS درخواست می‌دهد. endpoint و host از ورودی کاربر ساخته نمی‌شوند. redirect مسدود است، پاسخ محدود و timeout=3.5s است.
- سقف هر مأموریت و سقف روزانه سراسری از جدول `mission_routing_daily_usage` در تراکنش پایگاه داده کنترل می‌شوند. هر درخواست پولی **حتی در صورت خطا** از بودجه کم می‌شود. بدون سقف مثبت سرویس به‌صورت قطعی غیرفعال است.
- نمایش UI تنها پس از بازکردن بخش انتخابی فهرست: GET قابلیت رایگان است؛ POST زمانی می‌رود که کاربر **مبدأ را قبلاً انتخاب کرده** و روی دکمه محاسبه زمان بزند. فهرست و موقعیت OSM اختیاری در خرابی سرویس باقی می‌ماند.
- DTO پاسخ، فقط `duration_seconds` و `route_distance_meters` با provenance `provider_route_estimate`، `measured_at` و `availability_verified:false` را دارد؛ هیچ ETA برای پیاده‌روی از سرویس خودرو ساخته نمی‌شود.
- **فروشگاه واقعی/موجودی/قیمت فعلی تأیید نیست**. بسیاری از نام‌های Shop و تمامی شماره‌های تماس دیتاست مسابقه ساختگی‌اند.

## فعال‌سازی بعد از اعتبارسنجی عملی G1/G2

```dotenv
# PRIVATE SERVER ENV ONLY; not in Git / JS / user messages
NESHAN_ROUTING_ENABLED=0
NESHAN_ROUTING_API_KEY=
NESHAN_ROUTING_MAX_CALLS_PER_MISSION=0
NESHAN_ROUTING_DAILY_MAX_CALLS=0
```

برای فعال‌سازی، ابتدا گواهی کلید و scope، هزینه دقیق، سقف حساب، log masking، سهمیه خروجی و دسترسی محیط میزبانی را روی یک deployment کنترل‌شده تأیید کنید. تا آن زمان مقدارها باید صفر بمانند. برای آزمایش بامصرف فقط روی محیط جداگانه و سقف بسیار کوچک، بدون تماس خودکار CI و با آگاه‌سازی کاربر عمل کنید. کلید مسیریابی باید فقط بک‌اند باشد.

## گیت‌های تکمیل نسخه نهایی نقشه نشان (باز)

1. **MapLibre SDK وب و قفل وابستگی:** نسخه npm و CSS، کلید مستقلِ domain-scoped و attribution اجباری؛ تا زمان دریافت/تأیید کلید map SDK هنوز اضافه نشده است.
2. **نقشه چندپین با داده آفر معتبر:** sync کامل لیست و pin با result-set، fit-bounds و mobile RTL، fallback فهرست در قطع شبکه.
3. **Smoke حقیقی API:** Matrix car/motorcycle در تهران و محدودیت هزینه/quotas؛ Direction و pedestrian جداگانه آزموده شوند (نسخه walking در اسناد اختلاف دارد).
4. **امنیت و پذیرش:** ۱۲ سفر E2E، ۲۰ edge، manual accessibility/keyboard و تست دستگاه واقعی و deploy HTTPS.
5. **ارزیابی انسانی:** بنچمارک ۵۰ query دارای gold label و usability با کاربران واقعی هنوز ناتمام‌اند.

## آزمون‌های این PR

- Django mocked/zero-paid tests برای owner isolation، budget، invalid/old offer، نبود مختصات، stale result و fail-closed HTTP/JSON.
- Vitest برای قرارداد API، disabled UI و list-first fallback.
- Chromium fixture برای اطمینان از اینکه هنگام خاموش‌بودن سرویس، دکمه خرج‌کننده و ETA نمایش داده نمی‌شود.
- CI فقط پس از آماده شدن شاخه و یک‌بار روی آخرین SHA پایدار؛ هیچ فراخوانی به نشان در CI نباید رخ دهد.

مرجع: [ADR نشان](NESHAN-INTEGRATION-ADR-2026-10-23.fa.md).
