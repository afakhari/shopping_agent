# وضعیت واقعی پروژه و چک‌لیست تحویل | ۲۳ اکتبر ۲۰۲۶

> **آخرین وضعیت ممیزی ۲۳ اکتبر پس از PRهای #26، #28 و #29:** کد فعلی `main@e796d7a5aa96` و [CI پنج‌گانه موفق PR #29](https://github.com/afakhari/shopping_agent/actions/runs/39944085484) است؛ قابلیت گفت‌وگوی زمینه‌ای، تأیید دمو، مقایسه مستند و نمایش اختیاری موقعیت فروشنده منتخب اجرا شده‌اند. **نقشه چندپین نشان، ETA، اعتبارسنجی سرویس واقعی، UX انسانی، HTTPS عمومی و benchmark gold تکمیل نشده‌اند.** مطالب قدیمی این سند شواهد تاریخی‌اند. تصمیم پیش‌پیاده‌سازی: [ADR نشان](NESHAN-INTEGRATION-ADR-2026-10-23.fa.md).

> این سند «منبع واحد وضعیت فعلی» است. اسناد تاریخیِ ۲۲ اکتبر، PRD و معماری هدف را نباید به‌عنوان وضعیت فعلی خواند. آخرین کد بررسی‌شده: `main` در commit [`40b7d7744f`](https://github.com/afakhari/shopping_agent/commit/40b7d7744ff70e746935de5f7da5cb56d348a599). تغییرات صرفاً مستنداتی پس از آن ممکن است SHA اصلی را جابه‌جا کنند؛ موفقیت تست مربوط به **همین نسخه کد** است، نه تغییرات آینده.

## ۱. وضعیت بر اساس نوع شاهد

| قابلیت | شاهد | وضعیت |
|---|---|---|
| React RTL، Django/DRF، PostgreSQL، LangGraph و Docker | کد main و ۵ گیت CI [#39875797715](https://github.com/afakhari/shopping_agent/actions/runs/39875797715) برای PR #25 | **ادغام‌شده، CI سبز** |
| دیتاست اصلی | اجرای محلی Windows/Docker کاربر؛ `verify_dataset` | **۲۲۵٬۹۰۳ محصول / ۶٬۴۷۶ فروشگاه / ۳۳۱٬۵۰۶ آفر تأیید شد** |
| BoxAPI (provider=boxapi و مدل gpt-5.4-mini) | `BOXAPI_OK` و دو smoke با `--require-llm`، خروجی `LLM_RUNTIME=ACTIVE` و `intent_parser=llm` | **اتصال واقعی برای استخراج نیت خرید تأیید شد**؛ نه یک LLM مشاور تمام‌عیار |
| مسیر HTTP دیتاست واقعی | `SMOKE_RESULT=PASS` برای حالت `--skip-contact --require-llm` و `--full-journey --require-llm` | **در محیط محلی کاربر موفق** |
| شکست فروشنده و جایگزین | `no_answer` → ۵ آفر/۵ محصول پیشنهادی → `confirmed_available` دمو، idempotency، API مستقل visit-plan + persisted snapshot | **داده واقعی + استعلام کاملاً شبیه‌سازی‌شده** |
| سرعت جست‌وجو | ۴ ایندکس trigram با `valid=true`؛ Query Plan با Bitmap Index Scan؛ ۱٬۴۵۸ نتیجه برای «هدفون» | **۰٫۲۹ ثانیه برای یک درخواست HTTP محلی**؛ نه SLA/p95 |
| UX، GenUI و بازیابی SSE | PRهای #21، #24 و #25؛ ۵/۵ CI و Chromium در عرض‌های ۳۲۰، ۳۹۰، ۱۴۴۰ روی fixture مصنوعی | **تست خودکار موفق**؛ تأیید دستی آخرین نسخه روی موبایل واقعی لازم است |
| رفع نتایج تصادفی برای «احوال شما؟» | تصویر واقعی کاربر از ۱۲۰ کالای نامرتبط؛ guard مستقل frontend/backend، اصلاح replay و CI سبز PR #25 | **کد اصلاح و در main ادغام شد**؛ آزمایش مجدد کاربر پس از به‌روزرسانی محلی هنوز گزارش نشده |
| نقشه و تهران | انتخاب دستی محدوده، لیست فروشگاه، نقشه اختیاری OpenStreetMap، مشخص‌بودن فاصله مستقیم و ساعت ثبت‌شده | **fallback موجود**؛ ETA معتبر/مسیریابی چندمقصدی تأیید نشده |
| ارتباط واقعی با فروشنده | تنها ContactProvider شبیه‌سازی‌شده و با برچسب مشخص | **خارج از محدوده نمونه**؛ هیچ تماس واقعی برقرار نشده |
| نسخه عمومی HTTPS/Production | راهنمای امن و Compose production از نظر syntax بررسی شده‌اند | **استقرار عمومی و smoke URL عمومی تأیید نشده** |
| نسخه قابل‌ارسال داوری | سناریوهای متعدد تست شده، golden path موفق؛ `20/20` و `12/12` تکمیل نشده | **آماده‌سازی تحویل باز است؛ ویدئوی ~۵ دقیقه ضبط نشده** |

## ۲. دو اجرای واقعی کاربر با BoxAPI و دیتاست اصلی

**مسیر بدون تماس:** `docker compose exec -T backend python /tmp/smoke-golden-path.py --base-url http://frontend --skip-contact --require-llm`؛ نتیجه `SMOKE_RESULT=PASS; llm_used=yes; contact=skipped`. جست‌وجوی فشارسنج ۳۴۶ نتیجه، پنج SSE و بررسی شروط خرید موفق.

**مسیر کامل:** `docker compose exec -T backend python /tmp/smoke-golden-path.py --base-url http://frontend --full-journey --require-llm`؛ `LLM_RUNTIME=ACTIVE`، پنج SSE، نتیجه‌های کاتالوگ واقعی، `source_type=demo_simulation`، تکرار ایمن تماس، بازیابی از `no_answer`، ساخت و خواندن مجدد visit plan، `SMOKE_RESULT=PASS`. هیچ کدام به معنی تماس واقعی یا موجودی زنده نیست.

**پرفورمنس محلی (نمونه اندازه‌گیری):** `text_candidate_count`: 854.6ms→16.9ms، `eligible_product_count`: 6030.1ms→34.9ms، `full_search_page_size_1`: 2416.8ms→79.6ms؛ HTTP `localhost:8080` حدود 0.29s. منبع جزئیات: [گزارش عملکرد](CATALOG-SEARCH-PERFORMANCE.fa.md). نتایج فقط برای این سیستم/پرس‌وجو هستند.

## ۳. کارهای باقی‌مانده به ترتیب اولویت

1. **P0 | امنیت و قابلیت انتشار:** مشخص‌کردن host، HTTPS، secret manager، حفاظت از نرخ/سهمیه استفاده از BoxAPI (اعتبار ۳ دلاری)، مجوز نشست، CORS/CSRF، مشاهده‌پذیری و آزمون واقعی از URL عمومی. [#8](https://github.com/afakhari/shopping_agent/issues/8).
2. **P0 | UX و خطاهای واقعی:** روی main جدید، ورود «احوال شما؟» بدون درخواست خرید و بدون نتایج نامربوط را با مرورگر خود کاربر تأیید کنید؛ نمای ۳۲۰/۳۶۰/۳۹۰، keyboard/focus و axe؛ مرور تصویری مقایسه و plan. [#3](https://github.com/afakhari/shopping_agent/issues/3).
3. **P0 | کیفیت جست‌وجو و صداقت انتخاب:** مجموعه ۵۰ query برچسب‌دار، Recall@10 و MRR@10، صفر نقض شروط سخت و ارزیابی جست‌وجوی مبهم/برند/مدل/اعتبار در داده واقعی. [#4](https://github.com/afakhari/shopping_agent/issues/4).
4. **P1 | نقشه و مراجعه:** فهرست/نقشه همگام، مدیریت خطای سرویس، انتخاب اختیاری SDK و quota، ETA فقط با API تأییدشده، زمان و مسیر واقعی. [#5](https://github.com/afakhari/shopping_agent/issues/5)، [#7](https://github.com/afakhari/shopping_agent/issues/7).
5. **P1 | مأموریت ایجنت:** بازبینی checkpoint بومی LangGraph در برابر snapshot و guardهای فعلی، پوشش کامل خطاهای تماس و بازیابی پس از restart/قطع شبکه، بدون نقض approval. [#6](https://github.com/afakhari/shopping_agent/issues/6).
6. **P0 | تحویل مسابقه:** اجرای ماتریس [۲۰ سناریو](RELEASE-ACCEPTANCE-2026-10-23.fa.md)، **۱۲ مسیر مستقل E2E**، آزمون نسخه منتشرشده و ضبط **ویدئوی پنج‌دقیقه‌ای** از همان نسخه. [#8](https://github.com/afakhari/shopping_agent/issues/8).

## ۴. گیت و سیاست CI

- آخرین گیت روی commit کد #25: [quality-gates #39875797715](https://github.com/afakhari/shopping_agent/actions/runs/39875797715)، پنج job: frontend، backend-tests، browser-journey، backend-static-and-docs و production-compose-config، همگی `success`.
- CI هیچ کلید BoxAPI، دیتاست خصوصی یا تماس واقعی ندارد؛ مرورگر CI با داده fixture ساختگی اجرا می‌شود.
- **سبزبودن CI مساوی production-ready نیست.** برای اصلاح مستندات و Issueها، PR و CI تازه لازم نیست؛ یک commit docs-only و ویرایش Issue کافی است. برای تغییر کد مهم بعدی، یک PR تجمیعی و یک اجرای آخرین HEAD کافی است.

## ۵. راهنمای به‌روزرسانی محلی بدون حذف داده

```powershell
git status --short
git switch main
git pull --ff-only origin main
docker compose up -d --build backend frontend
docker compose ps
```

قبل از `git switch` تغییرات ذخیره‌نشده را نگه دارید. **`docker compose down -v` اجرا نکنید**؛ API key را در Git یا چت قرار ندهید. برای تست «احوال شما؟» صفحه را با `Ctrl+F5` تازه و در صورت نیاز «گفتگوی تازه» آغاز کنید؛ بعد یک درخواست واقعی مانند «هدفون تا سه میلیون تومان» بفرستید.

مرجع Issueها: [Backlog زنده](https://github.com/afakhari/shopping_agent/issues)؛ [اصول تفکیک شواهد و سناریوها](QUALITY.fa.md).
