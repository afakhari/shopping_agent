# دستورالعمل دستیار کدنویس — منبع مستقل پروژه

این سند برای هر عامل یا دستیار توسعه‌دهنده‌ای است که ممکن است بدون دسترسی به تاریخچه گفتگو به پروژه اضافه شود. **پیش از تغییر کد، این سند و فایل‌های لینک‌شده را بخوان.**

## 1. مأموریت

ساخت Bazaar Compass: دستیار خرید حضوری فارسی در تهران با React/TypeScript frontend، Django REST Framework backend، PostgreSQL و یک گراف محدود LangGraph. هدف نسخه داوری است: مسیر خرید باید دقیق، سریع، خوش‌ساخت و قابل‌نمایش باشد.

## 2. خواندن اجباری

1. `README.md`
2. `docs/index.fa.md`
3. `docs/product-spec.fa.md`
4. `docs/dataset-profile.fa.md`
5. `docs/data-dictionary.fa.md`
6. `docs/architecture.fa.md`
7. `docs/adr/` به ترتیب شماره
8. `docs/api-contract.fa.md`
9. `docs/agent-and-genui.fa.md`
10. `docs/ux-spec.fa.md`
11. `docs/testing-and-evaluation.fa.md`
12. `docs/deployment-runbook.fa.md`
13. `docs/next-step-backlog.fa.md`

## 3. وضعیت پیاده‌سازی را فرض نکن

در وضعیت فعلی، scaffold اولیه backend/frontend، health endpoints، UI shell و Docker Compose تعریف شده‌اند؛ با این حال نصب dependency و build/runtime هنوز تأیید نشده‌اند. همیشه `docs/implementation-status.fa.md` را بخوان و فایل‌ها و package scripts واقعی را بررسی کن. هیچ‌گاه نگو تست، build، migration، import یا deploy موفق بوده مگر فرمان واقعی اجرا شده و خروجی دیده شده باشد.

## 4. قواعد سخت کدنویسی

- شروط سخت خرید در سرور اعمال شوند و پیش از رتبه‌بندی باشند.
- برای شرط شهر دیگر، داده تهران را جعل/نسبت نده.
- `Offer` به `Product` و `Shop` از IDهای واقعی source وصل می‌شود. دسته فروشگاه جایگزین آفر محصول نیست.
- مبلغ با Decimal/Numeric در backend و رشته عددی در API؛ از float و JS unsafe integer دوری کن.
- `null`, رشته literal `null`, رشته خالی، JSON `[]` و `{}` متفاوت‌اند؛ importer آن‌ها را درست parse کند.
- timestampها timezone-aware باشند؛ نمایش زمانی با `Asia/Tehran`.
- شماره تماس دیتاست را برای تماس واقعی بیرونی استفاده نکن؛ حالت پیش‌فرض `DEMO_SIMULATION` است. UX لازم نیست مکرراً درباره جعلی بودن داده هشدار دهد.
- نتیجه تماس از simulator server-side می‌آید؛ client حق ارسال result/outcome ندارد.
- LLM SQL دلخواه، قیمت/موجودی/فاصله جعلی یا UI code اجراشدنی تولید نمی‌کند.
- Generative UI با union نوع‌دار و registry کامپوننت whitelist اجرا می‌شود.
- فیلتر/مرتب‌سازی UI نباید بی‌دلیل LLM call کند.
- API queryها parameterized باشند؛ timeout، validation و خطای ساختاریافته داشته باشند.
- secrets/dataset در Git نیستند؛ `.env.example` فقط placeholder دارد.
- سرویس جدید (Redis, Celery, Meilisearch, vector DB, WebSocket, runtime اضافی) بدون معیار یا benchmark اضافه نشود.

## 5. شیوه اجرای هر تسک

1. backlog ID/معیار پذیرش را انتخاب کن؛ اگر تسک تعریف نشده، اول آن را در backlog اضافه کن.
2. فایل‌های مرتبط و کد فعلی را بررسی کن؛ از بازنویسی غیرضروری خودداری کن.
3. حداقل تغییر کامل end-to-end انجام بده؛ API/DTO/UX/test/docs با هم هماهنگ باشند.
4. تست واحد برای rule جدید و integration/contract برای اتصال بین لایه‌ها بنویس.
5. lint/typecheck/test/build واقعی را اجرا کن، خروجی‌ها را خلاصه کن و شکست‌ها را پنهان نکن.
6. سند مرتبط را به‌روزرسانی کن؛ اگر تصمیم معماری عوض شد ADR را تغییر بده یا ADR جدید اضافه کن.
7. نتیجه را با مسیر فایل‌های تغییرکرده، دستورهای اجراشده، تست‌های موفق/ناموفق و کار باقی‌مانده گزارش کن.

## 6. سیاست مدل زبانی و هزینه

- prompt کوتاه، ساختاریافته و با context حداقلی.
- یک استخراج intent با schema؛ تکرار مدل فقط برای ابهام واقعی یا توضیح لازم.
- ابزارهای قطعی به جای پرسیدن مدل برای محاسبه قیمت، فاصله یا فیلتر.
- timeout، retry محدود، error mapping و fallback.
- مدل و provider از environment پیکربندی شوند؛ API key در frontend ممنوع.
- از chain-of-thought مخفی در UI یا log استفاده نکن؛ فقط خلاصه دلیل قابل‌بررسی ارائه کن.

## 7. خروجی هر مرحله باید قابل‌تحویل باشد

- **Data vertical slice:** CSV → importer → PostgreSQL → API → نتیجه قابل‌مشاهده.
- **Agent slice:** درخواست → state graph → tool → event → React component.
- **Recovery slice:** ابزار شکست می‌خورد → graph تشخیص می‌دهد → جایگزین منطبق → برنامه تازه.
- **Demo slice:** نسخه deploy شده + fixture پایدار + مسیر قابل‌تکرار.

## 8. وقتی با ابهام روبه‌رو شدی

ابتدا قراردادها و ADR را بررسی کن. اگر اطلاعات دیتاست اجازه نتیجه‌گیری نمی‌دهد، حدس را به فیلد حقیقت تبدیل نکن؛ نوع داده/وضعیت نامعلوم اضافه کن یا empty state مشخص ارائه بده. اگر تصمیم جدید بر زمان/ریسک اثر جدی دارد، پیشنهاد با گزینه‌ها و پیامدها ثبت کن؛ برای هر تغییر کوچک از کاربر تأیید نگیر، اما عملیات خارجی یا destructive را بدون مجوز انجام نده.

## 9. تعریف Done برای تسک

- معیار پذیرش backlog پاس شده.
- تست‌های مربوطه اضافه و اجرا شده‌اند.
- خطاهای جدید/کنسول در مسیر اصلی باقی نمانده‌اند.
- API و type frontend تطابق دارند.
- اسناد متأثر به‌روز شده‌اند.
- هیچ secret یا dataset حجیم به diff اضافه نشده.
- وضعیت واقعی اجرا (verified/not verified) صادقانه گزارش شده است.
