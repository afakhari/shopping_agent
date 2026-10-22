# برنامه جامع توسعه — Bazaar Compass

- نسخه سند: 1.0
- تاریخ پایه: 2026-10-21
- وضعیت کلی: scaffold اولیه B0 در کد ایجاد شده؛ کاتالوگ، importer، search و عامل هنوز پیاده‌سازی نشده‌اند. جزئیات آزمون واقعی در `implementation-status.fa.md` است.
- هدف: ساخت دمو محصولی برنده‌محور با کیفیت بالا در محدودیت زمان.

## 1. خلاصه اجرایی

Bazaar Compass کاربر را از شناخت نیاز تا انتخاب محصول، یافتن فروشنده واجد شرایط در تهران، مقایسه، استعلام کنترل‌شده و برنامه مراجعه راهنمایی می‌کند. UI فقط چت نیست؛ کارت، filter، comparison، map و visit plan ابزارهای مستقل‌اند. LLM برای فهم درخواست و ارکستراسیون محدود به‌کار می‌رود؛ قیمت، eligibility، فاصله و اتصال جداول در کد قطعی‌اند.

## 2. اهداف و non-goals

### هدف‌ها

- جست‌وجوی فارسی مقاوم در برابر اختلاف نوشتاری.
- نتیجه فقط در صورت وجود آفر و فروشنده واجد شرایط.
- فیلتر شروط سخت قبل از رتبه‌بندی و پیش از نمایش.
- توضیح شفاف قیمت ثبت‌شده، زمان منبع و وضعیت استعلام.
- عامل مرحله‌ای که failure را مدیریت و جایگزین پیدا کند.
- UI فارسی، RTL، موبایل‌محور و قابل استفاده با کنترل مستقیم.
- نسخه deploy شده و دموی پنج‌دقیقه‌ای قابل‌تکرار.

### خارج از هدف نسخه اول

خرید/پرداخت آنلاین، سفارش واقعی، تضمین موجودی زنده، تماس واقعی خودکار، پوشش بیرون از تهران، اپ موبایل native، آموزش مدل، چندعامل مستقل و زیرساخت با مقیاس عمومی.

## 3. معیار موفقیت و بارم‌بندی

بارم رسمی: محصول 75، UX 75، هوشمندی 50، دیپلوی 40، فنی 40، دیتاست 20، مجموع 300. قابلیت‌ها باید به یک معیار و یک تست پذیرش متصل باشند؛ فیچر تزئینی بدون اثر در جریان اصلی بعد از P0 است.

## 4. محدوده نسخه اول

P0: ingest CSV، Product/Shop/Offer، جست‌وجوی مستقیم، budget/credit/location filters، نتایج قابل‌مقایسه، مأموریت/گراف عامل، شبیه‌ساز تماس، جایگزین، برنامه مراجعه، UI responsive، tests، deploy.

P1: photo search، multi-item visit optimization، official public source checks، saving/sharing plan، richer indoor address guidance.

P2: voice, scheduled price tracking, notifications, search service replacement. این‌ها فقط پس از تثبیت P0 و با ارزیابی زمان/سود.

## 5. قراردادهای راهبردی

1. **Truth:** DB و ابزار نتیجه واقعی منبع حقیقت‌اند؛ متن مدل حقیقت جدید ایجاد نمی‌کند.
2. **Eligibility:** شروط hard server-side و قبل از rank هستند.
3. **No-result UX:** صفر نتیجه یعنی empty state قابل اقدام، نه نتایج نامنطبق.
4. **Search first:** مسیر جست‌وجوی ساختاریافته مستقل از LLM کار می‌کند.
5. **Agent as orchestrator:** LangGraph؛ ابزارهای داخلی محدود و schema-دار.
6. **GenUI as registry:** union type و کامپوننت‌های ثبت‌شده؛ هیچ اجرای UI کد تولیدی.
7. **Demo contact:** simulator سمت سرور با fixture قابل تکرار.
8. **No premature infrastructure:** سرویس تازه بعد از اندازه‌گیری اضافه می‌شود.

## 6. پشته منتخب

Frontend: React 19.3.0 + TypeScript 5.9.3 + Vite 8.3.5, Tailwind CSS 4.3.3, TanStack Query 5.104.3. Backend: Python 3.13, Django 6.1.2, Django REST Framework 3.18.2, Psycopg 3.3.6, PostgreSQL 17 container image. Tooling: Ruff 0.17.1, pytest 8.4.2, pytest-django 4.14.0; React lint: ESLint 9.39.1, Prettier 3.6.2, Vitest 5.0.5. نسخه‌های مستقیم در manifestها pin شده‌اند.

**محدودیت فعلی:** `frontend/package-lock.json` هنوز ایجاد نشده، چون registry.npmjs.org از محیط scaffold قابل‌دسترسی نبود. به همین دلیل dependencyهای انتقالی هنوز lock نشده‌اند؛ بعد از تولید lockfile باید Dockerfile به `npm ci` تغییر کند. این نسخه‌ها انتخاب پین‌شده manifest هستند، نه نتیجه یک install/build تأییدشده. دلیل انتخاب و گزینه‌های ردشده در ADRها آمده است.

## 7. فازهای توسعه و gate خروج

### Phase 0 — scaffold و قراردادها

**کار:** ساخت project files، dependency lockfiles، lint/type check، Docker، env config، docs and API schemas.

**خروج:** backend health endpoint، frontend shell، config validation و smoke test اولیه وجود داشته باشد. secretها در Git نباشند.

### Phase 1 — داده و import

**کار:** Product/Shop/Offer models، JSON parser، batch importer، report و idempotency.

**خروج:** شمارش ورودی با import تطبیق دارد، FK orphan مشخص، rerun تکراری نمی‌سازد، JSON parse errors گزارش می‌شوند و قیمت/timestamps نوع درست دارند.

### Phase 2 — جست‌وجو و UX بنیادی

**کار:** normalize Persian، query، join eligibility، filters، sort، pagination، React results, comparison.

**خروج:** تمام تست‌های hard constraints سبز؛ query profiling و benchmark ثبت شده؛ فیلتر در کلاینت fake نیست.

### Phase 3 — مأموریت عامل و GenUI

**کار:** mission state، LangGraph، node routing، tool schemas، typed events، registry کامپوننت‌ها، snapshot persistence.

**خروج:** مسیر normal و clarification اجرا، event sequence/reconnect کار می‌کند، malformed outputs کنترل می‌شوند، LLM outage جست‌وجوی مستقیم را از کار نمی‌اندازد.

### Phase 4 — استعلام و بازیابی از شکست

**کار:** deterministic contact simulator، contact history، outcomes، alternative search preserving constraints.

**خروج:** no-answer و unavailable testها از مسیر جایگزین به پیشنهاد منطبق می‌رسند؛ کلاینت نمی‌تواند outcome را جعل کند.

### Phase 5 — نقشه/برنامه مراجعه

**کار:** map provider smoke test، address parsing بدون ادعای داخل ساختمان، route provider optional و visit plan.

**خروج:** map failure fallback به list/address دارد؛ هیچ ETA بدون محاسبه route ساخته نمی‌شود.

### Phase 6 — دیپلوی و دمو

**کار:** env production، migrations/import، health, performance, browser smoke, demo fixtures, screen recording.

**خروج:** معیار Go در testing document پاس است؛ سناریوی 5 دقیقه‌ای بدون دخالت توسعه‌دهنده اجرا می‌شود.

## 8. ریسک‌ها

| ریسک | پاسخ |
|---|---|
| زمان کم و scope creep | P0 gate؛ P1 متوقف تا P0 پایدار باشد |
| محصول بدون offer | FK/join contract و integration tests |
| قیمت پرت | Decimal + quality flag + exclusion policy |
| خطای فارسی | normalizer مشترک و تست‌های متنی |
| provider یا network ناپایدار | adapter، timeout، retry محدود و fallback |
| نقشه غیرقابل‌دسترسی | smoke test زودهنگام و fallback list/address |
| agent hallucination | tool-only facts و typed DTO |
| demo غیرتکراری | fixtureهای server-side و scenario seed |
| کد وابسته به history chat | assistant guide کامل و docs index |

## 9. Definition of Done کلی

- user can complete product → eligible offer → shop comparison → contact scenario → alternative/plan.
- تمام شروط hard server-side و دارای tests هستند.
- داده اصلی و قیمت‌ها به source ID وصل می‌شوند.
- UI در موبایل و RTL قابل‌استفاده است.
- API، typeها و event schemas هماهنگ‌اند.
- quality/performance report ثبت شده.
- مسیر اصلی در deployment نهایی smoke-test شده.
- سند اجرا با کد جاری sync است.
