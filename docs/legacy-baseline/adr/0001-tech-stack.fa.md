# ADR-0001 — انتخاب پشته فنی

- وضعیت: پذیرفته‌شده برای نسخه داوری
- تاریخ: 2026-10-21

## زمینه

زمان محدود، تجربه فارسی/RTL و کارت/فیلتر مهم است. دیتاست بزرگ ولی رابطه‌ای است. مسیر عامل چندمرحله‌ای است اما نیازی به معماری توزیع‌شده در نسخه اول ندارد. سابقه توسعه‌دهنده با Django/React نیز ریسک اجرا را کاهش می‌دهد.

## تصمیم

- Frontend: React + TypeScript + Vite.
- UI: Tailwind CSS + shadcn/ui؛ کامپوننت‌های دامنه‌ای اختصاصی.
- server state: TanStack Query.
- Backend: Django REST Framework.
- DB: PostgreSQL.
- Agent: LangGraph، در صورت نیاز LangChain برای provider/tool adapters محدود.
- Stream: HTTP و در turns از SSE/fetch streaming.
- Container: Docker؛ هدف استقرار Liara پس از تست پلن/شبکه/extensions.

## گزینه‌های دیگر و دلیل رد/تعویق

- **Next.js:** ارزش SSR/SEO برای اپ کاربردی پس از login/mission کم است؛ Vite ساده‌تر است.
- **FastAPI:** قابل‌دفاع است اما Django REST Framework در الگوی پروژه و ORM/admin ecosystem ریسک کمتری دارد؛ هم‌زمان استفاده نشود.
- **Node backend / Mastra:** مستلزم انتقال منطق داده و اجرای Django یا داشتن دو backend است.
- **OpenAI Agents SDK:** جایگزین قوی برای گراف سبک؛ فعلاً به علت نیاز به graph صریح، LangGraph انتخاب شده است.
- **CrewAI/multi-agent:** پیچیدگی بدون نیاز اثبات‌شده.
- **Redis/Celery/WebSocket:** تا وقتی task پس‌زمینه/دوطرفه لازم نشود، اضافه نشود.
- **Meilisearch/vector DB:** بعد از benchmark search SQL.
- **CopilotKit/assistant-ui/Vercel AI SDK:** فقط اگر نمونه اتصال زمان را به شکل قابل‌اندازه‌گیری کاهش دهد.

## پیامدها

ساختار mono-repo و تعداد runtimeها کم می‌ماند؛ باید نسخه کتابخانه‌ها stable و locked باشند. این تصمیم performance claim نیست؛ جست‌وجو باید benchmark شود.

## شرایط بازنگری

- Django deployment/extensions مانع روشن ایجاد کند.
- query benchmark بعد از index/search tuning هنوز هدف latency را رد کند.
- آزمایش دو ساعته اتصال GenUI نشان دهد ابزار آماده به‌طور مادی زمان را کاهش می‌دهد بدون lock-in نامتناسب.

## نسخه‌های مستقیم در scaffold (هنوز نصب/تست نشده)

- Python base image: `3.13-slim`; Django `6.1.2`; DRF `3.18.2`; Psycopg `3.3.6`; Gunicorn `23.0.0` در requirements تولیدی.
- React/React DOM `19.3.0`; Vite `8.3.5`; `@vitejs/plugin-react` `6.1.2`; TypeScript `5.9.3`; Tailwind CSS/Vite plugin `4.3.3`; TanStack Query `5.104.3`; Vitest `5.0.5`.
- این‌ها version pinهای manifest هستند و تا نصب موفق dependencyها lock/verified محسوب نمی‌شوند. نسخه‌های انتقالی فرانت‌اند پس از تولید `package-lock.json` تثبیت خواهند شد.
