# Bazaar Compass | بازارکامپس

**دستیار هوشمند خرید حضوری تهران** | Tehran in-person shopping copilot.

> **وضعیت تأییدشده ۲۳ اکتبر ۲۰۲۶:** نسخه React/Django با دیتاست واقعی در محیط محلی آزمایش شده، مسیر شبیه‌سازی‌شده خرید تا برنامه مراجعه در سطح API موفق بوده و PRهای [#15](https://github.com/afakhari/shopping_agent/pull/15) تا [#19](https://github.com/afakhari/shopping_agent/pull/19) اصلاحات خرید اعتباری، داده فروشندگان، ساعات تهران، استعلام و مرورگر Chromium را به `main` اضافه کرده‌اند. **تست مرورگر اخیر با داده مصنوعی است؛ LLM واقعی، ETA نقشه، تست جامع دیتاست روی نسخه جدید، deployment عمومی و ویدئوی نهایی هنوز تأیید نشده‌اند.**

## مسئله
کاربر می‌خواهد از «نمی‌دانم چه بخرم» به «کدام کالا، از کدام فروشنده، با چه شرایطی و چه زمانی مراجعه کنم» برسد. پنج تجربه متصل: کشف محصول، مقایسه محصول، کشف و مقایسه فروشگاه، استعلام کنترل‌شده فروشنده، برنامه مراجعه و بازیابی شکست.

## اصول طراحی
- **فارسی، راست‌به‌چپ و موبایل‌اول** با دسترس‌پذیری و کنترل‌های واضح.
- **Chat + Workspace:** چت برای بیان نیاز؛ کارت، فیلتر، مقایسه و نقشه برای تصمیم.
- **داده‌محور:** آفر نشانه ثبت عرضه است، نه موجودی تأییدشده. در جهان شبیه‌سازی مسابقه، دیتاست داده معتبر است؛ پاسخ استعلام شبیه‌سازی‌شده برچسب مشخص دارد.
- **بدون نقض شروط سخت:** بودجه، برند صریح، روش پرداخت، محصول و محدوده بدون تأیید کاربر تغییر نمی‌کنند.
- **قابل ادامه:** وضعیت مأموریت باید پایدار و هر اقدام قابل تکرار ایمن باشد.
- **امنیت:** اسرار و دیتاست خام در Git قرار نمی‌گیرند؛ تماس/پیام واقعی فقط پس از تأیید و اتصال سرویس مناسب.

## نقشه اسناد
- [مشخصات و امتیازدهی](docs/PRODUCT.fa.md)
- [UX و وضعیت‌های لبه‌ای](docs/UX.fa.md)
- [معماری](docs/ARCHITECTURE.fa.md)
- [گردش‌کار ایجنت](docs/AGENT.fa.md)
- [داده و جست‌وجو](docs/DATA-SEARCH.fa.md)
- [قرارداد API پیشنهادی](docs/API.fa.md)
- [کیفیت و تست](docs/QUALITY.fa.md)
- [Backlog و مراحل تحویل](docs/ROADMAP.fa.md)
- [مراجع و الگوهای متن‌باز](docs/REFERENCES.md)
- [راهنمای مشارکت](CONTRIBUTING.md)

## انتخاب فنی
React + TypeScript + Vite، Django + DRF، PostgreSQL، LangGraph، controlled generative UI، MapLibre/سرویس نقشه سازگار با ایران. این‌ها **تصمیم معماری پیشنهادی** هستند؛ وضعیت اجرا در کد و خروجی تست تعیین می‌شود.

## کد نسخه پایه
پروژه شامل پوشه‌های `backend/`، `frontend/`، تنظیمات Docker و تست‌های اولیه است. [PR #9](https://github.com/afakhari/shopping_agent/pull/9) پس از اجرای موفق quality-gates روی شاخه وارداتی ادغام شد. برای وضعیت دقیق پیاده‌سازی و گام‌های بعدی، [گزارش تحویل](docs/DELIVERY-STATUS.fa.md) را ببینید.

## Competition
Scoring: Product 75, UX 75, Intelligence 50, Deployment 40, Engineering 40, Dataset 20 = **300**. Five-minute demo video is mandatory. The public data is a partial, selectively sampled Tehran catalog. All simulated merchant interactions must be clearly represented as simulated evidence.


## Current GitHub delivery status

- [Delivery status and outstanding steps](docs/DELIVERY-STATUS.fa.md)
- [Implementation issues and acceptance criteria](https://github.com/afakhari/shopping_agent/issues)
- [Workflow verification](https://github.com/afakhari/shopping_agent/actions/workflows/ci.yml)

**Important:** Full CI runs only on a PR becoming ready for review, manual dispatch, or version tags; it does not run on every development push. It still does not prove real dataset import, UX quality, browser journeys or production deployment. See [development policy](docs/DEVELOPMENT-POLICY.fa.md).

## Fast development and efficient CI

Development can be temporarily broken on feature branches. Run narrow local checks while iterating (`powershell -NoProfile -ExecutionPolicy Bypass -File scripts/quick-check.ps1 -Frontend` for Windows), then the full [quality-gates workflow](https://github.com/afakhari/shopping_agent/actions/workflows/ci.yml) at review/release milestones. The final candidate must be thoroughly verified. [سیاست تفصیلی](docs/DEVELOPMENT-POLICY.fa.md).

## راه‌اندازی سریع با دیتاست واقعی (ویندوز)

اسکریپت جدید ورود دیتاست از ZIP اصلی را به PostgreSQL انجام می‌دهد، تعداد رکوردها و شناسه‌های نمونه را کنترل می‌کند و سپس API جست‌وجو را آزمایش می‌کند. **هیچ داده خامی وارد GitHub نمی‌شود و GitHub Actions هم اجرا نمی‌شود.**

پیش‌نیاز: Docker Desktop روشن، Git و دریافت ZIP دیتاست از Sources پروژه. در PowerShell پس از clone مخزن اجرا کنید:

    powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-dataset.ps1 -ArchivePath "$env:USERPROFILE\Downloads\starcoach-dataset-v16-cap300-csv.zip"

[راهنمای کامل اجرای محلی](docs/LOCAL-DATASET-SETUP.fa.md) · [فرمان کنترل داده‌های واردشده](backend/apps/catalog/management/commands/verify_dataset.py)


## آماده‌سازی انتشار مسابقه

- [گزارش دقیق پوشش سناریوهای داوری و محدودیت‌های تأیید](docs/RELEASE-ACCEPTANCE-2026-10-23.fa.md)
- [راهنمای انتشار امن و آزمون پیش از دمو](docs/SAFE-PRODUCTION-2026-10-23.fa.md)
- [تست Chromium با داده ساختگی و شواهد تصویری](docs/BROWSER-E2E-2026-10-23.fa.md)

`quality-gates` اکنون علاوه بر تست‌های معمول Python/Node، یک مرحله مرورگر Chromium دارد. موفقیت این گیت ادعای آنلاین بودن نسخه production یا تماس واقعی با فروشگاه نیست.

## اتصال BoxAPI ویژهٔ هکاتون

[راهنمای فارسی دریافت اعتبار، تنظیم کلید خصوصی و آزمون واقعی BoxAPI](docs/BOXAPI-HACKATHON.fa.md).
هنگام انتخاب `LLM_PROVIDER=boxapi`، درخواست چت تنها از فیلدهای مستند `model` و `messages` استفاده می‌کند و توکن فقط به نشانی رسمی HTTPS BoxAPI ارسال می‌شود.
این اتصال در حال حاضر برای **استخراج نیت خرید** است؛ اطلاعات محصول، قیمت، موجودی و فروشگاه صرفاً از دیتابیس و ابزارهای معتبر ارائه می‌شوند.
