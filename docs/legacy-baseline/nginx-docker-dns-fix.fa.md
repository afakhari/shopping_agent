# رفع خطای DNS در Nginx هنگام شروع Docker Compose

## نشانه

در لاگ frontend پیام زیر دیده می‌شود:

```text
[emerg] host not found in upstream "backend" in /etc/nginx/conf.d/default.conf
```

بک‌اند ممکن است سالم باشد و health check آن پاسخ 200 بدهد؛ بااین‌حال Nginx وقتی `proxy_pass http://backend:8000/...` را به‌صورت ثابت در زمان بارگذاری پیکربندی resolve کند، ممکن است به‌علت زمان‌بندی شروع/راه‌اندازی مجدد سرویس‌ها خارج شود.

## اصلاح

در `frontend/nginx/default.conf` برای مسیر `/api/` از DNS داخلی Docker و متغیر در `proxy_pass` استفاده شده است:

```nginx
location /api/ {
    resolver 127.0.0.11 valid=10s ipv6=off;
    set $backend_upstream backend:8000;
    proxy_pass http://$backend_upstream;
    # سایر proxy headers و timeoutها باقی می‌مانند.
}
```

هنگام استفاده از متغیر، عمداً URI ثابتی به `proxy_pass` اضافه نشده است تا مسیر درخواست اصلی مانند `/api/v1/health/ready/` حفظ شود. `127.0.0.11` DNS داخلی Docker در شبکه‌های user-defined از جمله شبکه پیش‌فرض Compose است.

## اعمال روی Windows

از ریشه پروژه اجرا کنید:

```powershell
docker compose config --services
docker compose up -d --build --force-recreate frontend
docker compose ps
docker compose logs --tail=100 frontend
Invoke-WebRequest http://localhost:8080/healthz
Invoke-WebRequest http://localhost:8080/api/v1/health/ready/
```

اگر پورت برنامه در فایل `.env` به‌جای 8080 مقدار دیگری دارد، URL را با همان مقدار جایگزین کنید. خروجی نخست باید `ok` و خروجی دوم باید HTTP 200 بدهد.

## اگر حل نشد

```powershell
docker compose exec frontend nginx -t
docker network ls
docker compose ps
docker compose logs --tail=100 backend
```

اطمینان حاصل کنید که frontend و backend در یک شبکه Compose قرار دارند و service name در `docker compose config --services` دقیقاً `backend` است. از `docker compose down -v` استفاده نکنید، چون volume دیتابیس را حذف می‌کند.

## محدوده اصلاح

این تغییر جلوی شکست شروع Nginx به‌خاطر resolve شدن زودهنگام نام سرویس را می‌گیرد؛ به‌تنهایی خرابی واقعی شبکه Docker، نام سرویس اشتباه یا در دسترس نبودن backend را حل نمی‌کند.
