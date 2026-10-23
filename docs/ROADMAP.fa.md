# نقشه راه اجرای پروژه | به‌روزرسانی ۲۳ اکتبر ۲۰۲۶

مرجع رسمی شواهد: [وضعیت کنونی](CURRENT-STATUS-2026-10-23.fa.md)؛ بک‌لاگ زنده: [GitHub Issues](https://github.com/afakhari/shopping_agent/issues). وضعیت هر مورد از اجرای واقعی و CI ناشی می‌شود، نه صرفاً ایجاد کد.

| حوزه | تکمیل‌شده / شواهد | کار باز و ملاک خروج | Issue |
|---|---|---|---|
| زیرساخت و دیتاست | Django/React/Docker/PG، سبزشدن پنج گیت CI، verify_dataset روی 225903/6476/331506 و تست HTTP | تضمین امن بودن استقرار عمومی ذیل Release | [#2](https://github.com/afakhari/shopping_agent/issues/2) (گیت محلی تکمیل) و [#8](https://github.com/afakhari/shopping_agent/issues/8) |
| مکالمه و UX | RTL mobile-first، فرم‌ها و کارت‌های GenUI allowlist، برخورد با خطای SSE/502، «احوال شما؟» و تاریخچه غلط (#21/#24/#25)؛ Chromium fixture | بازآزمایی دستی آخرین build، ۳۶۰px و دستگاه واقعی، axe/accessibility، UX چند سناریو | [#3](https://github.com/afakhari/shopping_agent/issues/3) |
| کشف و مقایسه | تطبیق فارسی، hard filters، مقایسه تا ۳، PostgreSQL trigram، HTTP «هدفون» 0.29s در یک اجرا | golden 50 query، MRR@10/Recall@10، p95، کنترل برندی/مدلی و حاشیه‌های سخت | [#4](https://github.com/afakhari/shopping_agent/issues/4) |
| فروشگاه و نقشه | آفر معتبر، داده ساعت و نشانی، انتخاب دستی منطقه، OpenStreetMap اختیاری و fallback بدون ETA | لیست/نقشه هماهنگ، دسترسی و سهمیه سرویس معتبر، matrix/ETA واقعی و fallback شبکه | [#5](https://github.com/afakhari/shopping_agent/issues/5) |
| ایجنت و استعلام | LangGraph برای parse/search/render، state/event persisted، simulation، idempotency، recovery و BoxAPI واقعی برای intent | تضمین restart، نقاط approval، failure matrix و checkpoint/branching سطح PRD | [#6](https://github.com/afakhari/shopping_agent/issues/6) |
| برنامه مراجعه | داده اصلی، آفر جایگزین، استعلام no_answer→confirmed_available دمو و plan API + snapshot؛ browser fixture | تأیید دستی تجربه برنامه مراجعه/بازشدن نقشه و زمان حرکت واقعی | [#7](https://github.com/afakhari/shopping_agent/issues/7) |
| انتشار | تست واقعی محلی و [CI ۵/۵](https://github.com/afakhari/shopping_agent/actions/runs/39875797715) | **P0:** HTTPS public deploy، امنیت/rate limits BoxAPI، 20 edge cases، 12 E2E مستقل، video ~5min | [#8](https://github.com/afakhari/shopping_agent/issues/8) |

## ترتیب اجرایی بعدی
1. P0: تأیید UI نسخه جدید روی Windows بعد از #25، مخصوصاً «احوال شما؟» و قیود اعتبار؛ ثبت تصاویر و مسئله‌های واقعی.
2. P0: آماده‌سازی دامنه/هاست HTTPS و حفاظت از کلید و اعتبار BoxAPI پیش از استفاده عمومی؛ health و golden path از URL عمومی.
3. P0: آزمون ۲۰ مورد لبه‌ای و ۱۲ journey مستقل با داده مجاز، screenshot و accessibility، کنترل hard constraints.
4. P0: ضبط ویدئوی پنج‌دقیقه‌ای از **همان نسخه منتشرشده**؛ نه demo فرضی و نه تماس واقعی.
5. P1: بهبود کیفیت retrieval و نقشه/برنامه مراجعه بر اساس benchmark به‌جای افزودن vector DB یا multiagent بدون شاهد.

## سیاست PR و CI
برای هر milestone یک PR تجمیعی با تست روی آخرین commit؛ CI فقط در Ready-for-review، اجرای دستی milestone یا release tag. **اصلاح صرفاً مستندات/Issueها نیازی به PR و CI جدید ندارد.** اگر محصول در یکی از مسیرهای اصلی خطای بحرانی دارد، release متوقف بماند.
