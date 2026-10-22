# دستور برای دستیارهای توسعه و Coding Agents

ابتدا README.md و docs/PRODUCT.fa.md، docs/UX.fa.md، docs/ARCHITECTURE.fa.md، docs/AGENT.fa.md و docs/QUALITY.fa.md را مطالعه کن. ادعای تکمیل یا موفقیت تست فقط با خروجی واقعی همان تست مجاز است.

قواعد:
1. منبع حقیقت Product، Shop، Offer و نتایج ContactAttempt دیتابیس/ابزار هستند؛ LLM حق ساختن قیمت، موجودی، فاصله یا گارانتی ندارد.
2. تمام شروط hard در سرویس قطعی فیلتر شوند. تغییر بودجه/شعاع/شرایط پرداخت نیازمند تأیید کاربر است.
3. simulator باید server-owned، seedپذیر و قابل‌بازتولید باشد؛ تماس واقعی ادعا نشود.
4. React UI فقط رویدادهای ساختاریافته و کامپوننت‌های allowlist را رندر کند؛ اجرای کد HTML/JS تولیدی LLM ممنوع.
5. تمام ارقام فارسی/عربی/انگلیسی در ورودی نرمال شود؛ زمان مراجعه در Asia/Tehran سنجیده شود.
6. تست‌ها، typecheck، lint و build باید در PR گزارش شوند. داده خام، .env، token یا mock secret هرگز commit نشود.
7. معماری و دیتاست فعلی قابل بازنگری‌اند. بازنویسی کامل فقط پس از benchmark و مقایسه هزینه/فایده؛ کد سالم را کورکورانه حذف نکن.
8. هر PR باید user journey تحت‌تأثیر، acceptance criteria، تست انجام‌شده و screenshot موبایل/دسکتاپ (برای تغییر UI) را ذکر کند.
9. اولویت: end-to-end golden path و UX و runtime deployment، نه معماری پرزرق‌وبرق.
