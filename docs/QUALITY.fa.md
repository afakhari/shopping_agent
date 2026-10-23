# استاندارد آزمون، پذیرش و ارزیابی

> **وضعیت اجرایی:** آخرین CI کد #25 [۵/۵ سبز](https://github.com/afakhari/shopping_agent/actions/runs/39875797715)؛ مرورگر CI از fixture مصنوعی استفاده می‌کند. کاربر روی دیتاست واقعی دو مسیر LLM+HTTP را با PASS گزارش کرده است، اما هنوز ماتریس ۲۰ سناریو، ۱۲ مسیر مستقل، p95، axe و استقرار HTTPS تکمیل نشده‌اند. [گزارش مرجع](CURRENT-STATUS-2026-10-23.fa.md).

## Quality gates
Backend: Django check, migrations check, pytest, Ruff, import dry-run. Frontend: npm ci, typecheck, ESLint, unit tests, build. Integration: DB populated and 12 end-to-end journeys. Visual: screenshots width 360/390/768/1440، RTL، کنتراست، focus، keyboard، reduced-motion.

## مسیر طلایی
فارسی طبیعی → پیشنهاد مدل → جدول مقایسه → آفرهای معتبر → اصلاح بودجه یا شعاع → استعلام شبیه‌سازی‌شده → نتیجه ناموفق قابل‌بازتولید → گزینه پشتیبان → برنامه مراجعه.

## سناریوهای الزامی
۱) درخواست مدل دقیق
۲) درخواست بر اساس کاربرد
۳) درخواست مبهم و clarification
۴) صفر نتیجه و توضیح علت
۵) سقف بودجه سخت
۶) خرید اعتباری با محدودیت دسته/قیمت
۷) قیمت ثبت‌نشده
۸) فروشگاه صرفاً category-related بدون Offer
۹) ساعت کاری نامشخص/بسته
۱۰) پاسخ موفق seller simulator
۱۱) عدم پاسخ seller و fallback
۱۲) تغییر قیمت و validation دوباره
۱۳) پایان موجودی
۱۴) چند آفر با warranty متفاوت
۱۵) جابه‌جایی فیلتر هنگام request طولانی
۱۶) قطع شبکه و بازیابی snapshot
۱۷) مجوز موقعیت رد شد
۱۸) خطا در نقشه و fallback
۱۹) آدرس پاساژ بدون طبقه/واحد
۲۰) refresh حین استعلام بدون side effect تکراری

## سنجش جست‌وجو
پیشنهاد ۵۰ query برچسب‌دار از خود دیتاست؛ ارزیابی MRR@10، Recall@10، hard-filter violations (باید صفر)، latency p95. شرط قبول تغییر retrieval: رشد معنیدار نسبت به baseline بدون افزایش نقض شروط سخت.

## Product / UX
تست سناریو با کاربر بدون راهنمای شفاهی، success rate، تعداد تعامل تا انتخاب و زمان انجام کار. شکست به‌صورت واضح ثبت شود، نه اینکه در نمایش دمو پنهان شود.

## Performance
Core Web Vitals و p95 جست‌وجو در محیط مستقر سنجیده شود. هدف‌ها بعد از baseline ثبت شوند؛ ادعای تأیید آزمایش تا پیش از اجرای CI/Playwright ممنوع.

## امنیت/حریم خصوصی
تست جلوگیری از انتشار .env، API keys، شماره‌های حساس، دسترسی غیرمجاز به mission id، تزریق prompt، SSRF در URLهای خارجی، XSS در متن آفر و اجرای ابزار بدون approval.

## سیاست چرخه توسعه و هزینه CI

معیارهای آزمون بالا برای **نسخه نهایی** الزامی هستند، نه هر commit موقت. طی توسعه تست موضعی و بازبینی سریع انجام شود؛ CI جامع فقط با درخواست دستی، آماده‌شدن Draft PR یا release tag اجرا می‌شود. نتیجه تست‌های قبلی برای commit جدید قابل تعمیم نیست. [سیاست توسعه سریع](DEVELOPMENT-POLICY.fa.md).
