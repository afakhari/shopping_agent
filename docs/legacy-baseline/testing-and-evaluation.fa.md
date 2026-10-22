# راهبرد تست، ارزیابی عامل و عملکرد

هدف این سند تعریف شواهدی است که باید قبل از ادعای «آماده دمو» وجود داشته باشند. صرف اجرای بدون خطا در یک درخواست برای تأیید کافی نیست.

## 1. لایه‌های تست

1. **Unit:** normalization، parser JSON/null، اعتبار خرید اعتباری، quality قیمت، ranker، parser ساعات کاری و simulator.
2. **Integration:** import CSV → PostgreSQL → API جست‌وجو و آفر واجد شرایط.
3. **Contract:** نمونه request/response از `api-contract.fa.md` و event union در frontend/backend.
4. **Agent eval:** سناریوهای ورودی/وضعیت آغاز/انتظار خروجی و محدودیت‌ها.
5. **E2E:** مسیر اصلی با Playwright یا ابزار مشابه، مرورگر واقعی RTL و viewport موبایل.
6. **Performance:** benchmark صفحه اول query روی dataset کامل و اندازه‌گیری زمان API، DB query count و LLM tool turns.
7. **Deployment smoke:** health endpoints و اجرای یک سناریو در URL نهایی.

## 2. تست‌های داده

- تعداد رکوردهای واردشده با ورودی تطبیق داده شود.
- source ID تکراری و FK orphan گزارش شوند.
- literal `null`, empty string, `[]`, `{}` و JSON نامعتبر جداگانه آزمایش شوند.
- قیمت null/zero/negative/outlier درست مدیریت شود.
- قیمت از Python Decimal و API string باشد.
- UTC timestamp حفظ و در نمایش `Asia/Tehran` تبدیل شود.
- JSON nested برای specs/images/contacts/payment_options/weekly_hours/warranty parse شود.
- اجرای دوباره import، تعداد row را دو برابر نکند.

## 3. تست جست‌وجو و eligibility

سناریوهای اجباری:

- محصول با چند آفر → هر نتیجه اصلی آفر و Shop معتبر دارد.
- shop بدون offer محصول → هرگز به‌عنوان فروشنده آن محصول برنگردد.
- budget max → هیچ آفر خارج از سقف وارد نتیجه اصلی نشود.
- credit requirement → فقط shop دارای payment option با `channel=in_person`.
- channel `unknown` یا payment array خالی → در شرط سخت حضوری واجد نیست.
- empty result → هیچ گزینه خارج شرط نشان داده نشود و پیشنهاد تغییر شرط برگردد.
- q فارسی با `ي/ی`, `ك/ک`, ارقام و نیم‌فاصله → خروجی پایدار.
- pagination و sort نباید total غلط یا duplicate product تولید کنند.
- sort distance بدون origin → validation error.
- قیمت null/outlier از sort cheapest حذف شود.
- data set غیرتهران یا شهر دیگری به دروغ تهران فرض نشود؛ نسخه فعلی universe تهران است.

## 4. جدول ارزیابی عامل

| ID | ورودی/شرایط | رفتار مورد انتظار | خطای مسدودکننده |
|---|---|---|---|
| A01 | نیاز مبهم | فقط سؤال مؤثر بپرسد | پرسش‌های غیرضروری متعدد |
| A02 | نام/مدل مشخص | جست‌وجوی مستقیم ابزار | ساختن محصول خیالی |
| A03 | بودجه سخت | حفظ سقف | پیشنهاد بالاتر از سقف در نتایج اصلی |
| A04 | پذیرش اعتباری حضوری | channel exact in_person | گنجاندن unknown |
| A05 | صفر نتیجه | پیشنهاد تغییر شرط، بدون تغییر خودکار | نمایش گزینه نامنطبق |
| A06 | contact no_answer | ارزیابی گزینه بعدی | توقف بدون fallback |
| A07 | contact unavailable | حذف offer/shop ناسازگار از نتیجه نهایی | اعلام موجودی |
| A08 | contact closed | پیشنهاد گزینه مناسب برای زمان/محدوده | ادعای باز بودن |
| A09 | provider LLM unavailable | UI fallback و search مستقیم | ازکارافتادن کاتالوگ |
| A10 | malformed LLM output | validation/retry محدود | crash یا loop نامحدود |
| A11 | route provider unavailable | نشانی و fallback | ETA ساختگی |
| A12 | تماس simulator | نتیجه از fixture سرور | نتیجه انتخاب‌شده توسط کلاینت |
| A13 | refresh mission | بازیابی snapshot | از دست رفتن کل state |
| A14 | event duplicate/out-of-order | deduplicate/guard sequence | بازگشت UI به state قدیمی |
| A15 | نتیجه جایگزین | حفظ همه hard constraints | شل شدن پنهانی شرط |

## 5. معیارهای عملکرد اولیه

این اعداد هدف شروع‌اند، نه نتیجه benchmark:

- Catalog search API: p95 ≤ 500 ms برای query معیار، صفحه اول، محیط test مشخص و database warm.
- query count برای صفحه نتایج محدود و N+1-free.
- filter/sort بعدی: بدون LLM call.
- initial UI: render قابل‌استفاده حتی قبل از تکمیل قابلیت‌های اختیاری.
- stream: eventهای stage پیش از کارهای طولانی emit شوند؛ زمان provider جداگانه ثبت شود.
- memory import: خواندن CSV به صورت stream و batch، نه ساختن DataFrame کامل بزرگ در حافظه، مگر benchmark نشان دهد امن است.

هر benchmark باید commit hash، hardware/host، database state، warm/cold و تعداد تکرارها را در گزارش ثبت کند. عدد بدون شرایط اندازه‌گیری قابل مقایسه نیست.

## 6. دستورهای هدف

تا زمان ساخت اسکلت واقعی، این‌ها فرمان مورد انتظارند، نه لزوماً قابل اجرا در نسخه جاری:

```bash
# Backend
pytest
ruff check .
ruff format --check .

# Frontend
npm run lint
npm run typecheck
npm run test
npm run build

# Import/benchmark (فرمان نهایی با پیاده‌سازی importer مشخص می‌شود)
python manage.py import_dataset --source-dir data/raw --dry-run
python manage.py import_dataset --source-dir data/raw
```

در package/CI باید scriptهای واقعی با همین نام‌ها یا نام‌های ثبت‌شده در runbook وجود داشته باشند. مستندات را برای انطباق با ابزار انتخابی به‌روز کنید؛ فرمان خیالی را به عنوان تست موفق گزارش نکنید.

## 7. معیار Go/No-Go برای ضبط دمو

**Go** فقط اگر: smoke تست آنلاین موفق؛ import و تعداد روابط درست؛ جست‌وجو و budget/credit tests سبز؛ یک سناریو no-answer و یک سناریو جایگزین درست؛ هیچ secret در build/log نیست؛ هیچ P0 bug؛ refresh صفحه کارکرد اصلی را از بین نمی‌برد.

**No-Go** اگر: پاسخ یا قیمت ساختگی به‌عنوان واقعیت نشان داده شود؛ فیلتر hard بشکند؛ شماره/موجودی ابزار از کلاینت جعل شود؛ اجرای دمو به کلید محلی توسعه‌دهنده وابسته باشد؛ مسیر اصلی با خطای provider کاملاً متوقف شود.

## 8. اجرای مسیر طلایی روی سرویس واقعی محلی

اسکریپت `scripts/smoke-golden-path.py` با کتابخانه استاندارد Python، درخواست HTTP واقعی به سرویس محلی می‌فرستد؛ readiness و جست‌وجوی مستقیم را می‌سنجد، مأموریت می‌سازد، رویدادهای SSE را بررسی می‌کند، خروجی محصول و شروط سخت را اعتبارسنجی می‌کند و در حالت پیش‌فرض یک `DEMO_SIMULATION` ثبت می‌کند.

```powershell
python .\scripts\smoke-golden-path.py
python .\scripts\smoke-golden-path.py --query "هدفون بی سیم تا سقف ۳ میلیون تومان" --max-price-toman 3000000 --skip-contact
python .\scripts\smoke-golden-path.py --query "ماشین پرنده" --expect-empty --skip-contact
python .\scripts\smoke-golden-path.py --require-llm
```

`LLM_RUNTIME=ACTIVE` یعنی همین turn از adapter مدل خروجی معتبر دریافت کرده است. `agent_mode=model_configured` در health صرفاً می‌گوید کلید و نام مدل تنظیم شده‌اند و به‌تنهایی پاسخ‌گویی provider را اثبات نمی‌کند. جزئیات و عیب‌یابی در `docs/golden-path-smoke.fa.md` آمده‌اند. اسکریپت روی localhost کاربر در این محیط اجرا نشده؛ باید پس از بالا آوردن Docker و واردشدن دیتاست اجرا شود.
