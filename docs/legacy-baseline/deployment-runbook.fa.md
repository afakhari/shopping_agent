# Runbook توسعه محلی و دیپلوی

**راهنمای اجرایی اصلی برای Windows:** [`windows-setup-and-verification.fa.md`](windows-setup-and-verification.fa.md). برای اجرای مرحله‌ای lint/test/build/import از `scripts/verify-local.ps1` استفاده کن؛ این runbook جزئیات زیرساخت و دیپلوی را توضیح می‌دهد.


**وضعیت:** راهنمای راه‌اندازی محیط برای کد فعلی. API کاتالوگ و shell جست‌وجوی React پیاده شده‌اند، اما به دلیل نبود Docker و package registry در محیط تولیدکننده، راه‌اندازی کامل هنوز تأیید نشده است.

## 1. پیش‌نیازها

- Git.
- Python نسخه‌ای که در `backend/pyproject.toml` تثبیت خواهد شد؛ از version آزاد و مبهم پرهیز کنید.
- Node.js LTS و package manager تثبیت‌شده در lockfile (ترجیحاً npm در صورت نداشتن دلیل برای جایگزین).
- Docker و Docker Compose plugin.
- حدود فضای دیسک کافی برای ZIP و CSVهای خام (ZIP حدود 58 MB و CSVهای بازشده حدود 285 MB در snapshot بررسی‌شده؛ فضای دیتابیس و index جداگانه نیاز دارد).
- در صورت فعال‌بودن عامل: API key از ارائه‌دهنده مدل؛ پروژه بدون کلید باید حداقل catalog search را اجرا کند.

## 2. ساختار متغیرهای محیطی

`.env.example` مرجع نام متغیرهاست؛ مقدار secret واقعی داخل آن قرار ندهید.

| متغیر | توضیح |
|---|---|
| `DJANGO_SECRET_KEY` | secret بک‌اند، تصادفی و مخصوص محیط |
| `DJANGO_DEBUG` | فقط local true؛ production false |
| `DJANGO_ALLOWED_HOSTS` | hostهای مجاز |
| `DATABASE_URL` | اتصال PostgreSQL |
| `LLM_PROVIDER` | شناسه adapter واقعی پیاده‌شده |
| `LLM_API_KEY` | secret server-side؛ هرگز `VITE_` نداشته باشد |
| `LLM_MODEL` | مدل انتخاب‌شده پس از smoke test |
| `LLM_BASE_URL` | فقط اگر provider/base URL جایگزین لازم است |
| `AGENT_CONTACT_MODE` | `DEMO_SIMULATION` در دمو |
| `VITE_API_BASE_URL` | آدرس API که داخل bundle frontend قابل مشاهده است؛ secret نگذارید |
| `MAP_PROVIDER` | provider منتخب پس از smoke test |
| `MAP_API_KEY` | فقط اگر key قابل‌نمایش کلاینت طبق سیاست provider است؛ کلید محرمانه را build نکنید |

افزودن متغیر جدید مستلزم تغییر هم‌زمان `.env.example`, settings, docs و تست config است.

## 3. قرار دادن دیتاست

حالت پیشنهادی، ZIP را در `data/starcoach-dataset-v16-cap300-csv.zip` قرار می‌دهد. روش جایگزین:

```text
data/raw/products.csv
data/raw/shops.csv
data/raw/offers.csv
```

Importer هر دو حالت ZIP و پوشه استخراج‌شده را می‌پذیرد. قبل از import، مسیر را با `ls`/`dir` بررسی و dry-run اجرا کنید. `data/`, `.csv`, `.zip` در `.gitignore` قرار دارند. به هیچ وجه `git add -f` برای این فایل‌ها نزنید. فرمان دقیق در `import-and-search.fa.md` آمده است.

## 4. جریان توسعه محلی

```bash
cp .env.example .env
# مقادیر local را ویرایش کنید؛ secretها را commit نکنید.
docker compose up --build -d
# انتظار می‌رود backend ابتدا با DB آماده شود؛ از health endpoint برای تأیید استفاده کنید.
docker compose exec backend python manage.py migrate
# سپس dry-run و import واقعی مطابق docs/import-and-search.fa.md
```

نام serviceهای فعلی `db`, `backend`, `frontend` است. توجه کنید که Docker CLI باید روی ماشین اجراکننده نصب و در دسترس باشد.

## 5. ترتیب راه‌اندازی backend

1. متغیرهای محیطی را validate کن؛ در نبود DB startup یا readiness باید با خطای تشخیصی تمام شود.
2. migrationها را اجرا کن.
3. health live و ready را بررسی کن.
4. dataset import با dry-run و سپس واقعی.
5. summary و quality report import را نگه دار.
6. `catalog/search` و endpoint جزئیات را با داده‌ای معلوم تست کن.
7. agent را با stub/simulator تست کن؛ LLM provider جداگانه smoke test شود.

## 6. دیپلوی

- target اولیه Liara + Docker است؛ پیش از انتخاب image/DB addon، پلن واقعی و دسترسی extensionهای PostgreSQL را تأیید کنید.
- frontend به صورت build استاتیک deploy شود یا از web server container سرو شود.
- backend به صورت container؛ migrations به گام deploy مشخص وصل شوند.
- dataset باید به روش upload/mount/command مناسب platform منتقل شود، نه داخل image و نه از Git.
- secretها در secret/env manager میزبان قرار گیرند.
- `DEBUG=false`, `ALLOWED_HOSTS`, CORS, healthcheck, log output و timeoutها تولیدی تنظیم شوند.
- مسیر map و LLM در خود دامنه آنلاین آزمایش شود؛ دسترسی توسعه‌دهنده روی لپ‌تاپ کافی نیست.

## 7. Pre-demo checklist

- [ ] URL آنلاین در مرورگر ناشناس/دستگاه دیگر باز می‌شود.
- [ ] health live و ready سبز است.
- [ ] dataset import در همان محیط انجام شده و شمارش‌ها ثبت شده‌اند.
- [ ] جست‌وجو/فیلتر بدون LLM کار می‌کند.
- [ ] fixture استعلام با seed/profile مشخص تکرارپذیر است.
- [ ] نقشه یا fallback آدرس کار می‌کند.
- [ ] secretها در client bundle، source map عمومی یا log نیستند.
- [ ] داده و session اولیه برای دمو آماده است؛ سناریو نیاز به تایپ طولانی ندارد.
- [ ] refresh browser جریان اصلی را نمی‌شکند.
- [ ] قابلیت‌هایی که وجود ندارند در UI به صورت فعال نمایش داده نمی‌شوند.

## 8. عیب‌یابی

- **DB connection failed:** hostname، credentials، network/allowlist، ready status و migration را چک کنید؛ secret کامل را در chat/log چاپ نکنید.
- **JSON import error:** ردیف/فیلد/خط را گزارش کنید؛ `null` literal را به JSON null یا missing تبدیل کنید؛ CSV را با split نخوانید.
- **صفحه اول کند است:** SQL log/profiling، query count، `EXPLAIN ANALYZE`, index و payload size را بررسی کنید؛ قبل از افزودن موتور جست‌وجو benchmark بسازید.
- **CORS:** origin دقیق frontend را وارد allowlist کنید؛ `*` در production با credential استفاده نشود.
- **SSE قطع می‌شود:** proxy buffering/timeout، `Content-Type`, keep-alive, sequence و GET snapshot را بررسی کنید؛ ابتدا تشخیص دهید مشکل از network است یا graph.
- **نقشه دیده نمی‌شود:** key restriction، referrer policy، domain access، SSL و محدودیت سرویس را بررسی کنید؛ fallback list/address باید همچنان در دسترس باشد.
