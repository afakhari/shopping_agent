# Bazaar Compass | بازارکامپس

**دستیار هوشمند خرید حضوری تهران** | Tehran in-person shopping copilot.

> **وضعیت فعلی:** کد نسخه اولیه React و Django با [PR #9](https://github.com/afakhari/shopping_agent/pull/9) به `main` منتقل و CI شاخه وارداتی موفق شد. این فقط baseline قابل توسعه است؛ قابلیت‌های نسخه نهایی، واردکردن داده واقعی روی محیط عملیاتی، آزمون مرورگر و دیپلوی همچنان نیازمند اجرا و ارزیابی‌اند.

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
