# ADR-0002 — LangGraph، مرز عامل و Generative UI

- وضعیت: پذیرفته‌شده
- تاریخ: 2026-10-21

## زمینه

خرید دارای شاخه‌های clarification، search، eligibility، compare، contact result، alternative و visit plan است. داور باید جریان واقعی را ببیند؛ در عین حال کنترل UI، داده و تکرارپذیری ضروری است.

## تصمیم عامل

یک graph مرکزی LangGraph با typed state؛ logic قطعی در tool/serviceهای پایتون؛ LLM فقط intent parsing/clarification/tool selection/explanation. SQL آزاد، محاسبه قطعی مدل و نتیجه تماس انتخابی از سمت کلاینت مجاز نیست.

## تصمیم Generative UI

- React components ثبت‌شده برای `clarification`, `product_results`, `product_comparison`, `shop_results`, `contact_progress`, `alternative_options`, `purchase_plan`.
- discriminated union در TypeScript و معادل server-side schema.
- داده‌های محصول/قیمت/فروشگاه از services برگردد، نه از تولید آزاد مدل.
- HTML/JS/React تولیدشده توسط مدل اجرا نشود.
- fallback برای component نامعتبر و tool/provider error.

## Transport

HTTP برای search/filter؛ POST turn با SSE یا `fetch` streaming برای eventهای مراحل. event envelope شامل `schema_version`, `mission_id`, `seq`, `type`, `payload`. GET snapshot برای بازیابی وضعیت.

## تماس دمو

Simulator سمت سرور، outcomeهای seeded و قابل تکرار. UI نباید نتیجه simulator را در لاگ‌های داخلی به‌عنوان real phone call ثبت کند. حالت پیش‌فرض هیچ تماس واقعی بیرونی انجام نمی‌دهد.

## گزینه‌های رد/تعویق

CopilotKit + AG-UI، assistant-ui و Vercel AI SDK می‌توانند در prototype مقایسه شوند، اما وابستگی قطعی نیستند. A2UI و free-form generated UI برای نسخه اول لازم نیستند. چند-agent به تعویق افتاده.

## پیامدها

UI یکپارچه و تست‌پذیر است؛ تیم باید event schema و state persistence را توسعه دهد. graph در یک سرویس Django process اجرا می‌شود؛ platform جدا لازم نیست.

## شرایط بازنگری

نیاز به interoperable agent protocol با ابزارهای متعدد یا اثبات صرفه‌جویی قابل‌توجه در زمان/کیفیت از طریق framework آماده.
