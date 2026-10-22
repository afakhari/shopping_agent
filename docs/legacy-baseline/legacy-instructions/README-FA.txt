اصلاح خطای ساخت Docker در Bazaar Compass

فایل موجود در مسیر زیر جایگزین شود:
frontend/src/features/missions/MissionPanel.tsx

تنها اصلاح عملکردی: حذف متغیر hasRadiusField که تعریف شده بود اما استفاده نمی‌شد و به‌علت noUnusedLocals ساخت TypeScript را متوقف می‌کرد.

پس از استخراج در ریشه پروژه اجرا کنید:
  cd frontend
  npm run typecheck
  npm run lint
  npm test
  npm run build

سپس از ریشه پروژه:
  docker compose build --no-cache frontend

فقط اگر build با موفقیت تمام شد:
  docker compose up -d --force-recreate frontend
