# گزارش تحویل Sprint 2

**تاریخ:** 2026-10-21
**وضعیت:** کد پیاده‌سازی شده؛ runtime در این محیط به دلیل نبود Django/DRF و دسترسی به رجیستری وابستگی‌ها تأیید نشده است.

## قابلیت‌های تحویل‌شده

1. **Mission persistence:** مدل‌های `PurchaseMission`, `MissionEvent` و `ContactAttempt`، شناسه UUID برای مأموریت، شمارنده ترتیبی رویدادها و snapshot برای بازیابی پس از refresh.
2. **LangGraph:** مسیر محدود `parse_request → search_catalog → render_results` با fallback deterministic اگر LangGraph نصب نباشد.
3. **استخراج intent اختیاری با LLM:** `apps/agent/llm.py` از Chat Completions API سازگار با OpenAI استفاده می‌کند. تنها عبارت جست‌وجو، بودجه، شرط اعتباری و sort استخراج می‌شوند؛ تمام نتایج تجاری از دیتابیس می‌آیند. خروجی schema-validate و محدود می‌شود و خطا/timeout به parser قطعی fallback می‌کند.
4. **حفظ شروط:** شروطی که از متن کاربر استخراج می‌شوند پس از graph در Mission ذخیره می‌شوند تا validation تماس و جست‌وجوی جایگزین همان شروط را رعایت کنند.
5. **تماس شبیه‌سازی‌شده:** نتیجه از پیکربندی سرور و تعداد تلاش‌های مأموریت انتخاب می‌شود. کلاینت اجازه انتخاب outcome ندارد؛ تماس واقعی ارسال نمی‌شود. در نسخه فعلی فقط purpose بررسی موجودی فعال است.
6. **بازیابی بعد از شکست:** پس از عدم پاسخ/ناموجود بودن/بسته بودن، هم آفرهای همان محصول از فروشگاه‌های دیگر و هم محصولات جانشین هم‌دسته جست‌وجو می‌شوند؛ شروط بودجه، اعتباری و مکانی مجدداً اعمال می‌شوند. جانشین‌ها برای استعلام بعدی به candidateهای مأموریت افزوده می‌شوند.
7. **Generative UI محدود:** رابط React رویدادهای مأموریت، نتایج محصول، وضعیت استعلام و جایگزین‌ها را با کامپوننت‌های ثابت و کنترل‌شده نشان می‌دهد؛ کد یا HTML تولیدی از مدل اجرا نمی‌شود.

## تنظیم LLM (اختیاری)

در فایل `.env` خصوصی این متغیرها را تنظیم کنید:

```dotenv
LLM_ENABLED=1
LLM_PROVIDER=openai_compatible
LLM_API_KEY=...
LLM_MODEL=...
LLM_BASE_URL=https://api.openai.com/v1
LLM_TIMEOUT_SECONDS=6
```

برای endpoint سفارشی، `LLM_BASE_URL` باید ریشه API سازگار با `POST /chat/completions` باشد. کلید را به frontend یا Git commit نکنید. اگر کلید یا مدل تنظیم نشود، هیچ درخواست بیرونی ارسال نمی‌شود. Adapter یک تلاش محدود دارد و retry اضافه نمی‌کند تا latency و زنجیره خطا محدود بماند.

## بررسی‌های انجام‌شده

- `python -m compileall -q backend scripts`: موفق.
- `python scripts/verify_scaffold.py`: موفق.
- parse تمام فایل‌های `frontend/src` با TypeScript compiler API: موفق (syntax فقط، نه typecheck کامل).
- parse همه JSONهای پروژه و YAML مربوط به Compose: موفق.
- تست‌های جدید برای schema استخراج intent، نبود شبکه بدون تنظیم provider، persistence شرط‌های متن، شبیه‌سازی تماس و محصولات جانشین اضافه شده‌اند.

## موارد تأییدنشده

- `pytest` و `manage.py check/migrate`: در محیط سازنده ممکن نیست؛ Django و DRF نصب نیستند و PyPI قابل‌دسترسی نبود.
- درخواست به مدل واقعی: API key/model در اختیار نبود و شبکه بیرونی استفاده نشد.
- `npm ci`, typecheck/test/build: package dependencies از رجیستری نصب نشده‌اند.
- Docker build/up و اجرای کامل API با PostgreSQL: Docker CLI در محیط موجود نیست.

## معیار خروج از Sprint 2

Sprint 2 را فقط پس از اجرای موفق موارد زیر در محیط توسعه/CI دارای dependencies، PostgreSQL و provider لازم، runtime-verified اعلام کنید:

```bash
cd backend
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate
pytest -q
ruff check .
cd ../frontend
npm ci
npm run lint
npm run typecheck
npm test
npm run build
cd ..
docker compose config
docker compose build
docker compose up -d
```
