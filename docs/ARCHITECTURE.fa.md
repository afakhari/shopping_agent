# معماری هدف و مرز مسئولیت‌ها

## استک
Frontend: React/TypeScript/Vite، UI primitives قابل‌دسترسی، TanStack Query، design tokens.
Backend: Django/DRF، PostgreSQL، LangGraph، سرویس‌های قطعی domain.
Maps: SDK نشان/MapLibre (ارائه‌دهنده نهایی وابسته به تست کلید و سهمیه)، ماتریس مسیر فقط برای shortlist.
Deployment: Docker Compose برای development، production بر اساس verification واقعی لیارا.

## مرزها
Browser: intent form, filters, product compare, map, chat, mission status, snapshot recovery.
Django: authentication/session, request validation, pricing/offers, shop eligibility, geospatial shortlist, hours, contact attempt persistence, mission state & event sequence.
LangGraph: understanding, orchestration, human approval, branching/recovery; NO direct invention of catalog facts.
Contact provider: SimulationContactProvider سروری و قابل‌بازتولید؛ رابط RealContactProvider صرفاً extension point.
Postgres: source of truth: Products, Shops, Offers, Missions, ContactAttempts, Events, VisitPlans.

## اصول رویداد
هر تغییر مأموریت transactionally persist شود. رویدادها دارای seq، mission_id، event_type، timestamp، schema_version و payload allowlist باشند. UI پس از reconnect رویدادهای از seq دریافت‌شده را replay یا snapshot جدید را load کند. درخواست‌های اثرگذار idempotency_key داشته باشند.

## انتخاب جست‌وجو
در ابتدا normalization فارسی، سازگاری برند/مدل، pg_trgm، ranking و hard filters؛ سپس فقط در صورت benchmark مثبت pgvector یا موتور جدا. برای جغرافیا shortlist با Haversine؛ برای ETA رسمی Matrix API.

## امنیت
No secrets in frontend. Allowed tools فقط از سرور با credential. محدودیت نرخ و دسترسی به مأموریت. HTML/JS تولیدی مدل اجرا نشود. تمام user-facing source badges واقعی و قابل‌دفاع باشند.

## ADRهای مقدماتی
ADR-001: حفظ استک Django/React تا زمان evidence خلاف.
ADR-002: Controlled GenUI به‌جای generated executable UI.
ADR-003: single mission graph به‌جای multiagent orchestration غیرضروری.
ADR-004: seller simulation deterministic بر اساس fixture سرور.
ADR-005: API و UI مستقل از LLM در فیلترهای عادی.

## ریسک‌های عملیاتی
واردکردن دیتاست، سازگاری schema واقعی، کلید Maps، نرخ API، build روی Node/Python واقعی، لیارا، latency LLM، درستی migration، توان recovery after restart. بدون اجرای تست نباید status «آماده production» گزارش شود.


## تفاوت انتخاب هدف و استک فعلی (۲۳ اکتبر ۲۰۲۶)
- `React + Vite + Django/DRF + PostgreSQL + LangGraph` و GenUI با allowlist در main اجرا می‌شوند؛ **TanStack Query، سرویس نشان، Matrix ETA، Liara production و native LangGraph checkpointer** را صرفاً از ذکرشدن در طرح نمی‌توان اجراشده دانست.
- UI فعلی برای نقشه از نمای اختیاری OpenStreetMap و انتخاب دستی تهران استفاده می‌کند. فاصله مستقیم، ETA نیست.
- داده و state خرید در PostgreSQL persisted است، ولی agent graph کنونی فقط parse/search/render را اجرا می‌کند؛ استعلام و visit-plan در endpointهای Django/دامنه اجرا می‌شوند.
- `LLM_PROVIDER=boxapi` با آزمون واقعی کاربر برای intent فعال شده، از `/chat/completions` استفاده می‌کند و به backend محدود است؛ به کد frontend یا CI کلید داده نشده.
- برای status عملی و backlog [CURRENT-STATUS-2026-10-23.fa.md](CURRENT-STATUS-2026-10-23.fa.md) و Issues #5/#6/#8 مرجع‌اند.
