# رفتار ایجنت و شبیه‌سازی فروشندگان

## واحد کاری
یک ShoppingMission پایدار با state و events. تصمیم و فیلتر UI و وضعیت ایجنت روی همین مأموریت اعمال شوند.

## وضعیت‌ها
draft → intent_ready → exploring_products → comparing → selecting_shop → awaiting_contact_approval → contacting → evaluating_contact → (ready_to_visit | needs_recovery | awaiting_user_choice).

## حداقل گره‌ها
parse_intent؛ clarify_required؛ product_retrieve؛ product_rank؛ shop_filter؛ rank_visit؛ request_approval؛ contact_shop؛ evaluate_contact؛ propose_backup؛ build_visit_plan.
مسیر nonLLM deterministic باید برای جست‌وجو/فیلتر/خرید در دسترس بماند.

## نتیجه تماس
confirmed, unavailable, no_answer, price_changed, shop_closed, unknown/error. این‌ها شبیه‌سازی سروری با سناریوی seedپذیرند؛ **نه تماس واقعی**.

## سناریو
- confirmed: قیمت/موجودی/ساعت پرسیده‌شده؛ مرحله بعد برنامه مراجعه.
- no_answer: گزینه بعدی همان SKU را بدون تغییر hard constraints بررسی کن.
- unavailable: فروشگاه جایگزین همان SKU، سپس محصول جانشین در صورت تأیید.
- price_changed: دوباره محدودیت بودجه را اعتبارسنجی کن.
- closed: زمان مناسب با برنامه ساعت کاری و پیشنهاد فروشگاه دیگر.
- error: retry ایمن و fallback دستی.

## Human approval
تغییر محصول، تغییر شروط سخت، تماس حقیقی و هر خروجی دارای اثر خارجی باید قبل از اجرا تأیید شود. انتخاب همان فروشنده و صرفاً تغییر sort نیازمند LLM نیست.

## Persist/replay
از checkpoint پایدار استفاده کن؛ از thread/mission id ثابت، event sequence و idempotency key برای جلوگیری از تماس تکراری بعد از retry بهره ببر. UI مجاز است از آخرین snapshot بازسازی شود.

## محدودیت مدل زبانی
LLM فقط intent و توضیح پیشنهاد را پیشنهاد می‌کند. tool layer محاسبه قیمت، آفر واقعی، فروشنده و اعتبار خرید را تأیید می‌کند. خروجی JSON Schema + validation + allowlisted UI components. از اجرای کد تولیدی مدل جلوگیری کن.


## تفاوت معماری هدف با پیاده‌سازی فعلی (۲۳ اکتبر ۲۰۲۶)
- Graph فعال در `backend/apps/agent/graph.py` در حال حاضر **سه گره parse_request → search_catalog → render_results** دارد؛ تمام گره‌های PRD در ابتدای سند را نباید به‌عنوان زیرگراف مستقلِ اجراشده گزارش کرد.
- BoxAPI واقعی برای **استخراج نیت** با `LLM_RUNTIME=ACTIVE` روی محیط کاربر تأیید شد؛ کاتالوگ و hard filters قطعی‌اند و قیمت/موجودی را مدل اختراع نمی‌کند.
- مأموریت، event sequence و snapshot در PostgreSQL پایدارند؛ `client_request_id` برای استعلام دمو idempotent است. این با **checkpoint بومی کامل LangGraph** یکی نیست.
- احوال‌پرسی در UI و API سرور قبل از جست‌وجو از کاتالوگ و LLM جدا می‌شود (#25). پاسخ‌های backend social persisted و بدون کارت خرید ساختگی‌اند؛ replay نسخه‌های قبلی کارت‌های نامرتبط را فقط در نمایش پنهان می‌کند.
- سه‌گانه شکست فروشنده، جایگزینی واقعیِ واجد شرط و plan در آزمون `--full-journey --require-llm` با دیتاست مسابقه **در سطح HTTP محلی** موفق است؛ فروشنده حقیقی تماس نگرفته است.
- موارد باز: branch/restart پیشرفته، تعریف approval برای عملیات خارجی احتمالی آینده و error matrix کامل. [Issue #6](https://github.com/afakhari/shopping_agent/issues/6) / [گزارش وضعیت](CURRENT-STATUS-2026-10-23.fa.md).
