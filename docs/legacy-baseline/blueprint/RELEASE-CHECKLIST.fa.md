# چک‌لیست Release و تحویل مسابقه

## پیش از اولین استقرار

- [ ] کلیدها و متغیرهای محرمانه rotate و در GitHub Secrets/Liara ذخیره شدند.
- [ ] `git ls-files` هیچ `.env`، SQLite، dump، فایل CSV خصوصی، node_modules یا `.venv` ندارد.
- [ ] schema و migrations روی PostgreSQL واقعی اعمال شدند.
- [ ] دیتاست رسمی با checksum و cardinality import شد.
- [ ] health/live و health/ready درست عمل می‌کنند (ready داده را هم می‌سنجد).
- [ ] API و ترجمه خطا و داده‌های unknown تست شدند.
- [ ] map/LLM credentials در سرور/محدودیت دامنه نصب و quota تست شد.

## کیفیت فرانت‌اند

- [ ] `npm ci && npm run typecheck && npm run lint && npm test && npm run build` موفق.
- [ ] `lang=fa` و `dir=rtl` و تست همه portalها و مؤلفه‌های فرم.
- [ ] نمایش کارت‌ها در عرض‌های ۳۲۰/۳۶۰/۳۹۰/۷۶۸/۱۴۴۰ قابل‌قبول است.
- [ ] فهرست/نقشه sync و fallback map failure تست شد.
- [ ] budget, credit, area تغییر می‌کنند و constraints در سرور اعمال می‌شوند.
- [ ] تمامی دکمه‌ها دارای action، disabled و error state هستند.
- [ ] کیبورد/focus/screen reader و reduced-motion بررسی شدند.

## کیفیت backend و agent

- [ ] `python manage.py check --deploy` و تست‌های pytest/ruff سبزند.
- [ ] provider های external timeout و fallback دارند.
- [ ] no_answer/unavailable/price_changed/closed با fixture آزمایش شدند.
- [ ] contact attempt idempotent است؛ replay گراف duplicate ایجاد نمی‌کند.
- [ ] mission after reload/reconnect بازیابی می‌شود.
- [ ] خروجی visit plan شامل evidence، وضعیت و گزینه پشتیبان است.
- [ ] hard-constraint violations در Golden Set صفر.

## نسخه داوری

- [ ] URL عمومی HTTPS ثابت ثبت شده.
- [ ] نسخه deployed با همان نسخه commit/tag مشخص شده.
- [ ] روی موبایل حقیقی تجربه کامل تست شده.
- [ ] روی سایت نهایی سناریوی کامل با fixture سروری اجرا شده.
- [ ] ویدئوی حدود ۵ دقیقه با صدای توضیح و نمایش عملکرد ضبط شده.
- [ ] در دمو تماس شبیه‌سازی‌شده به‌عنوان تماس واقعی بیرونی معرفی نشده.
- [ ] در روز ارائه سناریوی fallback برای اختلال سرویس خارجی آماده است.
