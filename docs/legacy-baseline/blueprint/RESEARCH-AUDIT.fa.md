# ممیزی تکمیلی بازارکامپس و تصمیم‌های اجرایی

تاریخ: ۱۴۰۵/۰۷/۳۰ (۲۲ اکتبر ۲۰۲۶)

## محدوده و سطح اطمینان

- مبنای ممیزی کد: `bazaar-compass - Copy.zip`؛ تحلیل ایستا و بررسی ساختار فایل‌ها.
- مبنای اعداد: `reports/dataset-audit.json` و `docs/dataset-profile.fa.md` موجود در آرشیو؛ فایل CSV اصلی در آرشیو حاضر نیست.
- راستی‌آزمایی انجام‌شده در همین محیط: `python -m compileall -q backend scripts` موفق؛ `python scripts/verify_scaffold.py` موفق و ۳۷ مسیر ضروری را تأیید کرده است.
- اجرا نشده: Django migrations/pytest، اتصال به PostgreSQL، تست end-to-end مرورگر، استقرار Docker/Liara، اتصال واقعی LLM و API نقشه. علت: وابستگی‌ها و سرویس‌های مربوط در محیط ممیزی موجود نیستند.
- نکته: `frontend/package-lock.json` در آرشیو موجود است؛ سند قدیمی پروژه که نبود lockfile را گزارش می‌کرد، برای نسخه حاضر معتبر نیست. `backend/db.sqlite3` صفر بایت است و دیتابیس بارگذاری‌شده محسوب نمی‌شود.

## تصمیم نهایی فناوری

- React 19 / TypeScript / Vite 8 و TanStack Query را حفظ کن.
- Django / DRF / PostgreSQL و LangGraph را حفظ کن؛ تغییر چارچوب اصلی فقط با دلیل و benchmark.
- برای نقشه تهران: `@neshan-maps-platform/maplibre-sdk`، فایل CSS رسمی و کلید محدود به دامنه. REST key مسیریابی صرفاً در سرور. جزئیات: https://platform.neshan.org/docs/sdk/web/maplibre/neshan-maplibre-gl-js/
- برای سنجش زمان مسیر پس از pre-filter جغرافیایی: Neshan Distance Matrix API (ابتدا فقط ۵ تا ۱۰ فروشنده برتر؛ TTL کوتاه و خطایابی).
- برای جست‌وجو: نرمال‌سازی فارسی، مترادف‌ها، استخراج برند/مدل/دسته و مشخصات، pg_trgm و benchmark. صرفاً در صورت بهبود سنجه‌ها، pgvector/جست‌وجوی معنایی افزوده شود.
- برای UI: design tokens واحد، primitiveهای در دسترس، RTL بومی، state سازگار میان نقشه/فهرست/فیلتر/چت؛ استفاده انتخابی از shadcn/ui و Tailwind، نه تغییر یک‌باره تمام CSS.
- برای تست: Vitest، pytest، Playwright، axe و سنجه‌های Web Vitals.

## ایرادها و قابلیت‌های گمشده به ترتیب اهمیت

### P0: مسدودکننده تحویل

1. بسته به داده واقعی اجرای پایگاه داده ثابت نشده؛ دیتابیس SQLite همراه آرشیو صفر بایت است. اتصال DB در readiness کافی نیست. پس از import شمارش رکوردها، checksum/version dataset و یک query واقعی را کنترل کن.
2. استقرار واقعی، آزمایش نسخه موبایل و تست E2E هنوز تأیید نشده‌اند.
3. محدودیت rate، شناسه ناشناس مأموریت و بازیابی خطا/تکرار درخواست باید برای نسخه عمومی بررسی شوند. client_request_id در مدل وجود دارد ولی در create/turn برای idempotency اعمال نشده است.
4. خروجی رویداد SSE پس از محاسبه کامل تولید می‌شود؛ «progress لحظه‌ای» نیست. وضعیت واقعی کار مرحله‌ای و تأخیرهای واقعی تفکیک شود.

### P1: تأثیر مستقیم بر امتیاز محصول و UX

5. گراف فعلی صرفاً `parse_request → search_catalog → render_results` است؛ checkpoint یا interrupt پایدار ندارد. گذار وضعیت‌های select product → choose shop → approve contact → verify → recover → visit plan ساخته شود.
6. شبیه‌ساز فعلی بر اساس تعداد تلاش‌ها چرخه ثابت outcome انتخاب می‌کند و فقط `verify_availability` را قبول می‌کند. سناریوهای وابسته به mission + shop + offer، استعلام قیمت و ساعت کاری با نتیجه ساختاریافته و قابل‌بازتولید افزوده شود.
7. `serialize_offer` فیلدهای `seller_title`, `description`, `warranty` را نمی‌فرستد، در حالی‌که مدل نگه می‌دارد. DTO و کارت فروشنده گسترش یابد.
8. فیلتر خرید اعتباری صرفاً `channel=in_person` را بررسی می‌کند و محدودیت `min_price_toman`, `max_price_toman` و `category_names` هر option را در قیمت آفر لحاظ نمی‌کند. eligibility در سطح offer/provider اعمال شود. سه‌حالته unknown/declared/no eligible حفظ شود.
9. وضعیت ساعت کاری از `weekly_hours` (sat..fri / declared, closed, unsupported / shifts) استخراج و در منطقه زمانی Asia/Tehran محاسبه شود؛ حالت نامشخص ≠ بسته و «باز است» ≠ «هنگام رسیدن باز خواهد بود».
10. UI نقشه تعاملی و مسیر واقعی ندارد؛ لینک OSM صرفاً نقطه ثبت‌شده را باز می‌کند. فهرست و نقشه باید انتخاب و فیلتر مشترک داشته باشند.
11. `Product` با OR روی tokenهای query جست‌وجو می‌شود؛ آزمایش‌هایی با برند/مدل همزمان، نام محاوره‌ای و خطای تایپی لازم است. شرط‌های برند/مدل explicit باید hard/strong constraint شوند.
12. مقایسه specs نیازمند فهرست ویژگی‌های استاندارد به تفکیک دسته، شناسه مشترک attribute، normalize واحد و fallback به متن اولیه است. با ۳۴۲۸ دسته محصول نباید برای همه دسته‌ها قول مقایسه عددی بدهیم؛ ۳ تا ۵ دسته پرتکرار را اول پوشش بده.
13. URL یا مختصات فروشگاه را با دقت کاذب داخل پاساژ نمایش نده. از متن آدرس صرفاً mall/floor/unit را با source text و confidence استخراج کن.
14. هر مأموریت باید خروجی مستقل `VisitPlan` داشته باشد: محصول، offer اصلی، فروشنده پشتیبان، شیوه پرداخت، قیمت ثبت‌شده، وضعیت استعلام، نشانی، طبقه/واحد، ساعات بازبودن در لحظه رسیدن و وضعیت route/ETA.

### P2: کیفیت و پایداری

15. به جای `MissionPanel.tsx` با بیش از ۱۲۰۰ خط و چهار لایه CSS، components مستقل و توکن‌های یکتا ایجاد کن؛ این refactor را مرحله‌ای و همراه regression snapshots انجام بده.
16. API در برابر درخواست تکراری، ذخیره هم‌زمان، گم‌شدن اتصال، قطع API نقشه، خطای LLM، قیمت خالی، لاگ داده شخصی و image URLهای معیوب تست شود.
17. status `recent_change/stale` صرفاً سن آخرین «تغییر» قیمت است، نه سن اثبات اعتبار قیمت. برچسب متنی دقیق حفظ شود؛ ثبت آفر ≠ تأیید موجودی.
18. آستانه ۱۰۰ میلیارد تومان برای حذف قیمت‌های پرت یک تصمیم کیفی است، نه حقیقت داده؛ آفرها باید در دیتابیس بمانند. سیاست پنهان‌سازی از نتایج خرید در صورت لزوم صریح و آزموده باشد.
19. اتصال API نقشه/LLM با circuit breaker ساده، timeout و fallback. هزینه و quota باید بررسی شوند.
20. برای استفاده عمومی، entitlement ناشناس مأموریت، محدودسازی نرخ درخواست، انقضای داده و محرمانگی موقعیت بررسی شود.

## معماری پیشنهادی داده و state

- `Product`, `Shop`, `Offer` منبع حقیقت داده برگزارکننده‌اند.
- سرویس مشتق `OfferEligibility` تمام شروط سخت را با بررسی قیمت، credit/provider/category و محل اعمال می‌کند.
- `MissionState`: intent, constraints, selected_product_id, selected_offer_id, alternatives, consent_status, contact_attempts, visit_plan, last_revision.
- `ContactAttempt`: mission/shop/offer/purpose/outcome/source/simulated_at/confirmed_price/confirmed_hours/stock_evidence/scenario_version/idempotency_key.
- `VisitPlan`: snapshot مستقل و نسخه‌دار، قابل بازیابی، با منابع جدا برای هر فیلد.
- گراف: `understand → retrieve → compare → select → shortlist → approve → verify → {success, no_answer, out_of_stock, price_changed, closed} → recover/plan`.
- side effectهای خارجی نباید داخل نود replayable بدون idempotency اجرا شوند؛ checkpoint persistent در PostgreSQL.
- Streaming واقعی در صورت نیاز از worker/background event persistence + SSE retrieval؛ برای MVP ابتدا قابلیت جست‌وجوی قابل‌پیش‌بینی و پاسخ سریع اولویت دارد.

## UX پیشنهادی

- Home: یک ورودی مکالمه، ۳ نمونه هدفمند، انتخاب منطقه اختیاری؛ عدم مطالبه موقعیت از ابتدا.
- Discovery: کارت‌های واقعی محصول با توضیح دلیل پیشنهاد و مقایسه حداکثر ۳ گزینه.
- Shop Explorer: map/list toggle، chips فیلترهای فعال، Bottom Sheet فیلتر با CTA «نمایش N نتیجه»، فهرست با قیمت + شرایط پرداخت + فاصله/ETA برچسب‌دار.
- Contact: timeline عملیاتی دارای outcome واقعی شبیه‌سازی، انتخاب خودکار گزینه پشتیبان فقط بعد از مجوز کاربر و حفظ hard constraints.
- Ready-to-Go: کارت نهایی با share/copy/address، وضعیت استعلام و دستور مراجعه، بدون نیاز به خواندن تاریخچه چت.
- UI states: empty + explanation/relaxation، error/retry، loading، partial، unknown، off-hours، stale price، location denied، maps unavailable.
- دسترس‌پذیری: contrast، focus، keyboard، reduced motion، کنترل‌های لمس دست‌کم ۴۴px برای اعمال اصلی، aria-live برای تغییر نتایج.

## ارزیابی و پذیرش

- Golden set از حداقل ۵۰ پرسش متنوع واقعی مبتنی بر دیتاست و ۱۲ سناریو end-to-end ساخته شود. پرسش‌ها دسته محصول، برند/مدل، کاربرد، بودجه، قسطی، بدون نتیجه، جایگزین، نشانی پاساژ و عدم پاسخ را پوشش دهند.
- برای retrieval: Recall@10، MRR@10 و hard-constraint violations = صفر در پرسش‌های آزمون. رتبه‌بندی بدون داده ساختگی از مدل تأیید شود.
- برای UX: completion rate سناریو، تعداد گام تا انتخاب، برگشت به فیلتر، خطاهای ناوبری و زمان تا برنامه مراجعه ثبت شود.
- برای performance: p95 زمان جست‌وجو و زمان ارائه اولین نتیجه در شبکه موبایل، Web Vitals (LCP ≤ 2.5s, INP ≤ 200ms, CLS ≤ 0.1) پس از اندازه‌گیری.
- برای کارکرد: `python manage.py check --deploy`, migrations، DB import، `pytest`, `ruff`, `npm ci`, `npm run typecheck`, `npm test`, `npm run build`, Playwright، Docker smoke و تست دامنه نهایی.
- دموی ۵ دقیقه‌ای: مسئله → انتخاب و مقایسه → فروشنده/نقشه/اقساط → عدم پاسخ → فروشنده پشتیبان → برنامه مراجعه. داده و outcome باید server-owned و تکرارپذیر باشند.

## ابهام‌های قابل رفع فقط با آزمایش محیط واقعی

- فایل خام CSV در آرشیو حاضر نیست؛ shape کامل data و نمونه‌های مشخص باید در محیط دارای فایل اصلی دوباره وارسی شوند.
- پایداری نصب نسخه‌های dependency، مهاجرت و اجرای pytest/TS build بررسی نشده‌اند.
- کلید API معتبر نشان، سهمیه، دامنه whitelisting و کیفیت شبکه روی محل استقرار هنوز در اختیار ممیزی نبوده‌اند.
- تعرفه و دسترسی LLM واقعی و latency آن اندازه‌گیری نشده‌اند.
- UI روی Android/iOS واقعی و نسخه آنلاین هنوز تست عملی نشده‌اند.
- خود ویدئوی اصلی چالش در ورودی حاضر نیست؛ تحلیل بر اساس شرح متنی و رونوشت ارائه‌شده است.

## منابع کلیدی

- https://platform.neshan.org/docs/sdk/web/maplibre/neshan-maplibre-gl-js/
- https://platform.neshan.org/docs/api/routing-category/distance-matrix/
- https://docs.langchain.com/oss/python/langgraph/interrupts
- https://langchain-ai.github.io/langgraph/concepts/durable_execution/
- https://baymard.com/research-articles/how-to-design-applied-filters
- https://baymard.com/blog/ecommerce-filter-ui
- https://www.postgresql.org/docs/current/pgtrgm.html
- https://playwright.dev/docs/emulation
- https://web.dev/articles/vitals
- https://operations.osmfoundation.org/policies/tiles/
- https://github.com/liara-cloud/django-getting-started
