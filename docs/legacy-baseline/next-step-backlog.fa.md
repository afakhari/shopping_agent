# Backlog اجرایی و معیارهای پذیرش

شناسه‌های backlog باید در commit/PR و گزارش دستیار کدنویس ذکر شوند. ترتیب زیر ترتیب پیش‌فرض است؛ dependencyهای فاز قبل gate فاز بعد هستند.

## B0 — آماده‌سازی پروژه

### B0-01: ساخت scaffold backend — کد نوشته شده، پذیرش runtime در انتظار تست
**وضعیت:** ساختار ایجاد شده؛ تا زمان نصب dependencies و اجرای `manage.py check`/`pytest` این مورد `[NOT VERIFIED]` است.
- ایجاد `pyproject.toml` یا dependency manifest با نسخه تثبیت‌شده، Django project، apps و settings split.
- افزودن Ruff، pytest/pytest-django و type checks متناسب با انتخاب ابزار.
- معیار پذیرش: install و `manage.py check` با env محلی اجرا شود؛ secret hard-code نباشد.

### B0-02: ساخت scaffold frontend — کد نوشته شده، پذیرش runtime در انتظار تست
**وضعیت:** فایل‌ها و تست‌ها ایجاد شده‌اند؛ رجیستری npm از محیط توسعه فعلی قابل‌دسترسی نبود و `package-lock.json` تولید نشده. بعد از تولید lockfile باید `npm ci`, lint, typecheck, test و build اجرا شود.
- React + TypeScript + Vite، ESLint, formatter, typecheck, test runner.
- Tailwind و shadcn/ui پس از بررسی نسخه compatible؛ RTL پایه.
- معیار پذیرش: `npm ci`, lint, typecheck, test, build موفق.

### B0-03: Docker و configuration — تعریف شده، build تأیید نشده
**وضعیت:** فایل‌های Dockerfile/Compose/nginx نوشته شده‌اند؛ Docker CLI در محیط ایجادکننده موجود نیست.
- PostgreSQL, backend, frontend/static-serving در Compose.
- readiness health check و env validation.
- معیار پذیرش: راه‌اندازی از clean checkout مطابق runbook، بدون credential واقعی.

## B1 — import و مدل داده

### B1-01: تعریف Product / Shop / Offer
**وضعیت:** `[IMPLEMENTED] / [NOT VERIFIED]`
- مدل‌ها و migrationهای اولیه در `apps/catalog/models.py` و `migrations/` نوشته شده‌اند.
- source IDs به‌عنوان PK نگه داشته شده‌اند؛ FKها به شناسه‌های منبع اشاره می‌کنند.
- Decimal برای قیمت، timestamp timezone-aware و JSONField برای داده تو‌در‌تو.
- Gate باقی‌مانده: `makemigrations --check`, migrate و model tests در محیط دارای Django.

### B1-02: JSON/null parser
**وضعیت:** `[IMPLEMENTED] / [NOT VERIFIED]`
- parserهای JSON، null، bool، decimal، timestamp، coordinate و نرمال‌سازی فارسی نوشته شده‌اند.
- Gate باقی‌مانده: اجرای تست‌های `apps/catalog/tests.py`.

### B1-03: importer streaming و batch
**وضعیت:** `[IMPLEMENTED] / [NOT VERIFIED]`
- `import_dataset` از ZIP یا دایرکتوری، dry-run، batch upsert، strict JSON، کنترل duplicate/missing IDs و orphan را دارد.
- اجرای مجدد idempotent است؛ batchها جداگانه transaction دارند.
- Gate باقی‌مانده: اجرای dry-run روی داده کامل و ورود واقعی در PostgreSQL.

### B1-04: گزارش ممیزی ماشینی
**وضعیت:** `[PARTIAL]`
- گزارش JSON و Markdown شامل row/unique ID، JSON خطادار، FK orphan، قیمت/زمان/مختصات نامعتبر، قیمت نامثبت/پرت و شمارش insert/update تولید می‌شود.
- هنوز گزارش field-level null coverage، پوشش تصویر/spec و تحلیل توزیع timestamp در فرمان importer کامل نشده؛ ممیزی موجود در `dataset-profile.fa.md` از اسکن مستقل دیتاست آمده است.

## B2 — جست‌وجو و API

### B2-01: Persian normalizer
**وضعیت:** `[IMPLEMENTED] / [NOT VERIFIED]`
- ي/ی، ك/ک، ارقام و نیم‌فاصله نرمال می‌شوند؛ مقدار display خام حفظ می‌شود.
- unit tests پایتون و TypeScript نوشته شده‌اند.

### B2-02: `GET /catalog/search/`
**وضعیت:** `[IMPLEMENTED] / [NOT VERIFIED]`
- جست‌وجوی query، فیلتر آفر، pagination و `total` محصولات یکتا در SQL.
- APIهای جزئیات محصول، offers و shop نیز نوشته شده‌اند.

### B2-03: hard filters
**وضعیت:** `[IMPLEMENTED] / [NOT VERIFIED]`
- budget، پذیرش حضوری اعتباری، origin/radius و پیش‌نیازهای sort پیاده‌سازی شده‌اند.
- تست‌های قطعی برای اعتبار، شعاع و empty result نوشته شده‌اند.

### B2-04: price quality policy
**وضعیت:** `[IMPLEMENTED] / [NOT VERIFIED]`
- null/zero/negative/outlier، Decimal و آستانه تنظیم‌پذیر؛ قیمت خام در DB حفظ می‌شود.
- آفر بی‌قیمت فقط در نبود سقف بودجه می‌تواند نمایش داده شود؛ outlier از رتبه‌بندی حذف می‌شود.

### B2-05: benchmark queries
- داده کامل، query set ثابت، warm/cold run، EXPLAIN ANALYZE.
- معیار: baseline report ثبت شود؛ فقط بعد از آن search engine extra تصمیم‌گیری شود.

## B3 — رابط بنیادی

### B3-01: application shell RTL
**وضعیت:** `[IMPLEMENTED] / [NOT VERIFIED]`
- application shell فارسی/RTL و responsive CSS پیاده شده؛ viewport/browser test باقی است.

### B3-02: search form + abort stale query
**وضعیت:** `[IMPLEMENTED] / [NOT VERIFIED]`
- debounce ورودی، TanStack Query و `AbortSignal` پیاده شده‌اند.
- query state هنوز در URL sync نشده است.

### B3-03: product and offer cards
**وضعیت:** `[IMPLEMENTED] / [NOT VERIFIED]`
- title/image/brand/category، قیمت و timestamp، آدرس، تعداد آفر و fallback عکس.
- build/typecheck/browser test باقی است.

### B3-04: comparison and empty state
**وضعیت:** `[PARTIAL]`
- کنترل sort/budget/credit، pagination و empty state پیاده شده.
- فهرست آفرهای همان محصول با بودجه/خرید اعتباری همسان از داخل کارت قابل بازکردن است؛ مقایسه هم‌زمان چند محصول با انتخاب چند کارت هنوز ساخته نشده است.

## B4 — مأموریت عامل/GenUI

### B4-01: Mission/Events models and API
**وضعیت:** `[IMPLEMENTED] / [NOT VERIFIED]`
- مدل‌های `PurchaseMission`, `MissionEvent`, `ContactAttempt`، UUID، state JSON و sequence یکتا ایجاد شده‌اند.
- API ساخت مأموریت و GET snapshot نوشته شده است.
- Gate باقی‌مانده: migration و API tests در محیط دارای Django/PostgreSQL.

### B4-02: LangGraph minimal workflow
**وضعیت:** `[IMPLEMENTED] / [NOT VERIFIED]`
- گراف پایه `parse_request → search_catalog → render_results` به `product_search_page` متصل است؛ fallback deterministic هم برای محیط حداقلی وجود دارد.
- adapter اختیاری LLM سازگار با OpenAI در `apps/agent/llm.py` پیاده شده؛ نیازمند تست runtime با کلید و مدل واقعی است.
- Gate باقی‌مانده: graph tests، dependency install و ارزیابی کیفیت parsing.

### B4-03: UI union contract
**وضعیت:** `[PARTIAL]`
- کامپوننت‌های `product_results`, `empty_state`, `contact_progress`, `alternative_options` به‌صورت payloadهای محدود emit می‌شوند؛ `MissionPanel` آن‌ها را رندر می‌کند.
- TypeScript union و registry عمومی هنوز باید جداگانه سخت‌گیرانه‌تر شوند.
- Gate باقی‌مانده: typecheck کامل، payload malformed tests و fallback برای component ناشناخته.

### B4-04: SSE/fetch stream
**وضعیت:** `[IMPLEMENTED] / [NOT VERIFIED]`
- envelope نسخه‌دار و sequence افزایشی در API؛ frontend از POST + fetch reader پیام‌های SSE را parse و event تکراری را حذف می‌کند.
- GET snapshot برای بازیابی موجود است؛ فرانت‌اند شناسه مأموریت و فیلترهای مرتبط را در sessionStorage نگه می‌دارد و در refresh رویدادها، نتایج و استعلام‌های قبلی را از snapshot بازسازی می‌کند.
- stream فعلی eventهای ذخیره‌شده یک نوبت را پس از اجرای گراف ارسال می‌کند، بنابراین هنوز token-level/live node streaming نیست.
- Gate باقی‌مانده: اجرا پشت Nginx و تست قطع اتصال/بازیابی در مرورگر واقعی.

### B4-05: provider adapter and fallback
**وضعیت:** `[IMPLEMENTED] / [NOT VERIFIED]`
- adapter محدود به OpenAI-compatible chat completions، schema validation، timeout حداکثر 10 ثانیه و fallback deterministic پیاده شده است. Retry عمداً اضافه نشده تا latency و زنجیره خطا محدود بماند.
- معیار باقی‌مانده: تست runtime با provider واقعی و اندازه‌گیری p95؛ وقتی adapter خاموش یا ناموفق است، کاتالوگ همچنان کار کند.

## B5 — تماس و بازیابی

### B5-01: server-side contact simulator
**وضعیت:** `[IMPLEMENTED] / [NOT VERIFIED]`
- outcome از `DEMO_CONTACT_OUTCOMES` و شمار تلاش‌های همان مأموریت انتخاب می‌شود؛ کلاینت اجازه انتخاب outcome ندارد.
- `ContactAttempt` دارای `source_type=demo_simulation` است؛ تماس واقعی انجام نمی‌شود.
- Gate باقی‌مانده: تست تکرارپذیری API و صحت migration.

### B5-02: alternative search
**وضعیت:** `[IMPLEMENTED] / [NOT VERIFIED]`
- پس از outcome ناموفق، آفرهای همان محصول از فروشگاه‌های دیگر و محصولات جانشین هم‌دسته برمی‌گردند؛ فیلترهای بودجه/اعتباری/محدوده دوباره اعمال می‌شوند و candidateهای جانشین به مأموریت اضافه می‌شوند.
- Gate باقی‌مانده: تست no-answer→same product alternative/substitute product و no eligible alternatives در runtime.

### B5-03: purchase plan DTO/UI
- selected shop/backup/address/time/price/contact status/action links.
- معیار: اطلاعات plan از source/tool می‌آید؛ هیچ ETA تخمینی ساختگی نیست.

## B6 — نقشه، کیفیت نهایی و دمو

### B6-01: Map provider smoke test
- test domain, key restriction, marker, link, responsive.
- معیار: map unavailable → list/address fallback.

### B6-02: Address hints
- extract known pasáž/floor/unit phrases from original address; preserve raw text.
- معیار: no invented indoor path.

### B6-03: End-to-end eval suite
- scenarios listed in testing document; CI where practical.
- معیار: all blocker scenarios green.

### B6-04: Production deploy
- migrations, import, secrets, healthchecks, logs, allowed hosts/CORS.
- معیار: clean browser on deployed URL passes main journey.

### B6-05: Five-minute demo assets
- fixed mission, product selection, contact scenarios, route fallback, recovery steps.
- معیار: can present within ~5 min without source-code tour.

## ترتیب ممنوع

P1/P2 را قبل از گذر از gates جست‌وجو، hard filter، import، UI اصلی و استقرار مسیر دمو شروع نکنید. هیچ task بدون acceptance criteria بسته نشود.
