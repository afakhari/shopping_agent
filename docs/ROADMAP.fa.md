# نقشه راه اجرایی و اولویت‌ها

وضعیت: اسناد پایه در GitHub منتشر شده‌اند. انتقال نسخه local baseline و build/test عملیاتی هنوز باید انجام شوند. شمارش کار انجام‌شده تنها با merge PR و شواهد CI معتبر است.

## P0 - Repo baseline / Green CI
- انتشار امن کد پاک‌سازی‌شده در PR مجزا، بدون secret/dataset.
- نصب وابستگی‌ها در GitHub Actions و اجرای backend/frontend check.
- import dry-run و یکپارچگی واقعی دیتاست در محیط مجاز.
- smoke تست health، جست‌وجو و مأموریت.

## P1 - Discovery & compare
- بازآرایی React به feature boundaries، design tokens یکپارچه.
- parser intent + نرمال‌سازی فارسی؛ ranking قابل ارزیابی.
- product cards، مقایسه مشخصات و state قابل ویرایش.

## P2 - Shop explorer
- offer eligibility در سطح shop/offer و پرداخت اعتباری.
- list/map یکپارچه، geofence، ساعات کار، نشانه‌های پاساژ.
- آزمایش Neshan SDK/route matrix با مدیریت cache و fallback.

## P3 - Agent mission
- LangGraph persisted checkpoint + typed event contracts.
- SimulationContactProvider برای stock/price/hours.
- سناریوهای failure/backup، approval، idempotency.
- کارت Visit Plan.

## P4 - Polish and release
- E2E و accessibility، performance benchmark و visual regression.
- دیپلوی و smoke test روی public URL.
- سناریوی دموی ۵ دقیقه‌ای با fixture شبیه‌سازی پایدار.

## ضدالگوها
بازنویسی فوری بدون baseline benchmark، multiagent غیرضروری، vector DB قبل از ارزیابی، live price بدون evidence، ساخت HTML توسط LLM، تکیه بر UI پر از پیام‌های ابزار.
