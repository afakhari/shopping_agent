# الگوهای Generative UI و طرح اصلاح رابط خرید | ۲۳ اکتبر ۲۰۲۶

## مطالعات انجام‌شده
1. assistant-ui Generative UI: https://www.assistant-ui.com/docs/tools/generative-ui — واژگان مشخص، JSON محدود و render مبتنی بر allowlist.
2. CopilotKit AG-UI: https://www.copilotkit.ai/ag-ui — همگامی وضعیت ایجنت و UI، اقدامات کنترل‌شده و human-in-the-loop.
3. Google A2UI component gallery: https://a2ui.org/reference/components/ — مشخصات توصیفی اجزا و محدود کردن دامنه action.
4. Vercel multi-step GenUI: https://vercel.com/academy/ai-sdk/multi-step-and-generative-ui — نتیجه tool به کارت عملیاتی و تفکیک loading/result/error.
5. OpenAI UI Guidelines: https://developers.openai.com/plugins/concepts/ui-guidelines — کارت مختصر، حداکثر یک عمل اصلی، و نمایش تدریجی داده.

این‌ها **مرجع الگو** هستند؛ هیچ کتابخانه یا پروتکل جدیدی به استک React/Vite/Django/LangGraph اضافه نشده است.

## یافته مشخص در کد فعلی
کامپوننت `alternative_options` از رویداد واقعی بک‌اند شامل `alternatives` و `alternative_products` بود، اما در `GenUIRenderer` صرفاً کارت fallback عمومی تولید می‌کرد. در همان حال `MissionPanel` گزینه‌ها را دوباره داخل کارت محصول نمایش می‌داد؛ تجربه تکراری و متناقض بود.

## اصلاحات این شاخه
- `RecoveryOptions` کارت اختصاصی فروشنده پشتیبان با یک اقدام واضح و گروه مدل‌های جایگزینِ قابل بازکردن ایجاد می‌کند.
- `verify_offer` تنها پس از کلیک مستقیم کاربر صادر می‌شود؛ قبل از تماس، offer و shop باید در snapshot قبلی همان مأموریت وجود داشته باشند؛ بک‌اند نیز مجدداً hard filters را بررسی می‌کند.
- دو نمایش تکراری گزینه‌های جایگزین ادغام شدند؛ توضیح شواهد تماس زیر `details` قرار گرفت.
- پروتکل دریافت `ui.component` تنها نام‌های شناخته‌شده را می‌پذیرد، از کامپوننت تودرتوی ناشناخته صرف‌نظر می‌کند و تعداد فرزندان stack را محدود می‌کند.
- هیچ قیمت یا موجودی ساخته نمی‌شود؛ نتیجه استعلام همچنان شبیه‌سازی سروری است.

## وضعیت تست
- تست‌های واحد `genui-types.test.ts` و `recovery-options.test.ts` برای قرارداد، داده خراب، تایید منبع و عدم اجرای action نادرست افزوده شدند.
- این تغییر عمداً فقط در شاخه `work/genui-patterns-consolidated` قرار دارد. **هیچ PR و هیچ CI جدیدی ایجاد یا اجرا نشده است.**
- پیش از آماده‌شدن برای merge، lint/typecheck، npm test موضعی و مرور تعاملی Chromium روی ۳۲۰/۳۹۰/۱۴۴۰ و داده ساختگی باید بررسی شوند.

## ادامه طراحی در همین شاخه
مسیر اصلی بعدی: خلاصه وضعیت مأموریت در خارج از چت، کارت‌های مقایسه متمرکز روی تفاوت‌ها، هماهنگی لیست و نقشه فروشگاه‌ها و گیت نهایی شواهد ۲۰ سناریو. از افزودن آزادانه component توسط مدل، HTML/JS تولیدی و فریم‌ورک تازه بدون benchmark پرهیز شود.


## مرور رقبا و پژوهش UX (نسخه تکمیلی)
- Google Shopping AI Mode (https://blog.google/products-and-platforms/products/shopping/google-shopping-ai-mode-virtual-try-on-update/): آغاز با نیاز طبیعی، پیشنهاد تصویری، narrowing و پیوند به داده محصول. **اقتباس:** مشخصات کوتاه و هدایت تدریجی. **عدم اقتباس:** ادعای موجودی/قیمت لحظه‌ای بدون داده به‌روز.
- Alexa for Shopping / Rufus (https://www.aboutamazon.com/news/retail/alexa-for-shopping-ai-assistant): راهنمای خرید پویا، توضیح دسته، مقایسه وابسته به هدف. **اقتباس:** مقایسه تفاوت‌های واقعی دو یا سه محصول.
- Perplexity Instant Buy (https://www.perplexity.ai/help-center/en/articles/10352906-what-is-instant-buy): کارت‌های قابل اقدام به‌جای متن بلند. **اقتباس:** کارت بازیابی/فروشگاه با یک اقدام؛ checkout واقعی در محدوده مسابقه نیست.
- Baymard Product List UX (https://baymard.com/research-articles/current-state-product-list-and-filtering): وضعیت شفاف فیلترها و قابلیت مقایسه؛ برای کالای فنی، تفاوت‌ها در یک جدول در دسترس باشند. **اقتباس:** سطرهای ویژگی و کنترل «فقط تفاوت‌ها»، خلاصه فیلترهای فعال و انتخاب مقایسه قابل پاک‌کردن.
- Baymard Listing Information (https://baymard.com/research-articles/product-listing-information): مشخصات دسته‌ایِ تصمیم‌ساز روی کارت؛ **اقتباس:** انتخاب حداکثر دو مشخصه موجود دیتاست بر اساس نوع محصول.

## اصلاحات تکمیلی همین شاخه
- همگام‌سازی محدودیت‌های استنتاج‌شده `turn.completed.constraints` میان Django و React؛ رفع نمایش بودجه/اعتبار ناهماهنگ با نتایج.
- انتخاب ۲ تا ۳ ویژگی فنی ثبت‌شده بر اساس نوع محصول (بدون ساخت مقدار).
- چیدمان مقایسه feature-first، سه محصول حداکثر، گزینه «فقط تفاوت‌ها»، اصلاح اعتبار اعتباری در سطح **Offer**.
- نمایش فیلترهای فعال کنار نتیجه با دسترسی مستقیم به فرم ویرایش. حذف اتوماتیک شروط سخت ممنوع است.
- کوتاه‌سازی کارت فروشنده؛ نشانه‌های «ارزان‌ترین/نزدیک‌ترین» صرفاً در **فروشندگان بارگذاری‌شده**؛ جزئیات آدرس/گارانتی/نقشه در `details`.
- به‌روز کردن تست مرورگر برای باز کردن `details` پیش از پیش‌نمایش نقشه.

## مستندات آزمون و مرز ادعا
تست‌های جدید Vitest: `product-highlights.test.ts`, `comparison-view.test.ts`, `seller-highlights.test.ts`, `recovery-options.test.ts` و `genui-types.test.ts`. 
اجرای CI عمداً صفر است، تا تمام تغییرات UX در همین شاخه آماده شوند. وضعیت فعلی **کد ثبت‌شده + آزمون‌های تعریف‌شده** است، نه قبولی این آزمون‌ها در GitHub.
