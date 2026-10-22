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
