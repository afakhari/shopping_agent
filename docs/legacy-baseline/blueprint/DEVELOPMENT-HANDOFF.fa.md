# راهنمای اجرای گام‌به‌گام برای تیم یا عامل کدنویس

## شروع کار: حقیقت موجود در برابر هدف

این بسته شامل کد نمونه قبلی و سند هدف است. بازسازی کامل `frontend/src/features/missions/MissionPanel.tsx` مجاز است، اما فقط همراه تست regression. سند اصلی: `MASTER-DEVELOPMENT-PLAN.fa.md`؛ خط قرمزها: اعتبار داده، consent برای تماس، رعایت hard constraints، بازیابی مأموریت و RTL.

## توالی پیشنهادی PRهای کوچک

1. **PR01 Infrastructure**: Clean repo/CI, docker compose postgres, migrations import readiness, secret policy. خروجی: تکرارپذیری و smoke.
2. **PR02 Domain**: OfferEligibility provider/min/max/category tri-state + decimal DTO + unit tests؛ در UI هنوز تغییری لازم نیست.
3. **PR03 Search**: نرمال‌سازی برند/مدل، benchmarks و relevance reasons؛ تفکیک hard/soft، case tests.
4. **PR04 Design Tokens**: RTL direction, typography, accessible primitives, story/screenshot fixtures و shell صفحات؛ بدون وابستگی به LLM.
5. **PR05 Discovery+Compare**: کارت محصول و مقایسه با category registry؛ نمایش null و evidence.
6. **PR06 Shop Explorer**: Neshan adapter/map list, credits, hours, fallback؛ geo integration tests.
7. **PR07 Mission Persistence**: schema revision، checkpointer و actions approve/reject، resume integration.
8. **PR08 Contact**: simulator fixtures price/hours/stock + idempotency + recovery tests.
9. **PR09 VisitPlan**: snapshot مستقل و deterministic reasons + address evidence.
10. **PR10 Finalization**: E2E، performance/a11y، telemetry، deployment و demo.

## قواعد برای هر PR

- فقط scope مرتبط با PR تغییر کند؛ contract changes با test و changelog همراه باشد.
- راه‌حل بدون گواه تست اجراشده «انجام شد» تلقی نشود. اگر provider دسترسی ندارد mock صریح و fallback تست شود.
- هیچ کتابخانه‌ای صرفاً برای ظاهر مدرن اضافه نشود. پشتیبانی فارسی، اندازه bundle، accessibility و maintenance بررسی شود.
- migrations باید backwards safe باشند؛ داده خام CSV هرگز با اصلاحات مدل نوشته نشود.
- `git diff --check`, lint/typecheck/tests و snapshot mobile قبل از merge.
- هر task با acceptance criterion و گواهی اجرا ثبت شود.

## دستورات شروع

```bash
cp .env.example .env
# مقادیر نمونه را با کلیدهای واقعی خود جایگزین کنید؛ .env را commit نکنید.
docker compose up --build
# نصب frontend در صورت اجرای محلی خارج Docker:
cd frontend && npm ci && npm run typecheck && npm run lint && npm test && npm run build
# backend از راهنمای backend/README.md؛ نصب وابستگی‌ها، مهاجرت و تست را انجام دهید.
```

`docker compose up` به فایل CSV رسمی و تنظیمات محیطی وابسته است و در این بسته صحت اجرای آن تأیید نشده. حجم دیتاست و اعتبار سرویس‌ها باید در محیط اجرا فراهم شوند.
