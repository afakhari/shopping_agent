# وضعیت واقعی پیاده‌سازی

- آخرین بازبینی کد و بررسی‌های ایستا: 2026-10-22؛ بازبینی UX/UI، بهبود خوانایی موبایل، هدف‌های لمس، فوکوس صفحه‌کلید، فرم‌های انتخابی Generative UI و حالت‌های انتظار/خالی.
- `[IMPLEMENTED]` یعنی کد نوشته شده است؛ این برچسب به‌تنهایی به معنی اجرای موفق runtime نیست.
- `[VERIFIED]` فقط برای بررسی‌ای استفاده می‌شود که در همین محیط واقعاً موفق شده باشد.

## وضعیت اجزا

| بخش | وضعیت | جزئیات و محدودیت |
|---|---|---|
| اسناد محصول و مهندسی | `[IMPLEMENTED]` | مشخصات محصول/UX، معماری، ADRها، قرارداد API، importer، جست‌وجو، تست، دیپلوی و راهنمای دستیار کدنویس در `docs/` هستند. |
| Git محلی | `[IMPLEMENTED]` | مخزن محلی موجود است؛ اتصال/مخزن آنلاین GitHub تأیید نشده است. |
| Backend scaffold و health | `[IMPLEMENTED] / [NOT VERIFIED]` | تنظیمات Django/DRF و endpointهای health نوشته شده‌اند؛ runtime تست نشده است. |
| Product / Shop / Offer | `[IMPLEMENTED] / [NOT VERIFIED]` | مدل‌ها و migrationهای `0001_initial` تا `0003_shop_in_person_credit_flag` شامل فلگ مشتق‌شده و ایندکس‌دار پذیرش اعتباری حضوری. `makemigrations --check` و `migrate` اجرا نشده‌اند. |
| CSV/ZIP importer | `[IMPLEMENTED] / [NOT VERIFIED]` | `import_dataset` دارای preflight، dry-run، parserهای نوع‌دار، upsert دسته‌ای و گزارش JSON/Markdown است. هنوز روی Django/PostgreSQL اجرا نشده است. |
| صحت ساختاری CSV داده‌شده | `[VERIFIED]` | اسکن streaming مستقل با Python استاندارد: 225,903 محصول، 6,476 فروشگاه، 331,506 آفر؛ شناسه تکراری/خالی، JSON خراب و FK یتیم مشاهده نشد. این مورد جایگزین تست importer نیست. |
| API جست‌وجو و مقایسه | `[IMPLEMENTED] / [NOT VERIFIED]` | `/api/v1/catalog/search/`, `/api/v1/products/{id}/`, `/api/v1/products/{id}/offers/`, `/api/v1/shops/{id}/` نوشته شده‌اند؛ اجرای runtime در دسترس نبود. |
| شروط سخت خرید | `[IMPLEMENTED] / [NOT VERIFIED]` | فیلتر بودجه، خرید اعتباری حضوری، مبدأ/شعاع Haversine، صفحه‌بندی و حذف قیمت صفر/منفی/پرت در سرویس query نوشته شده‌اند. |
| کیفیت قیمت | `[IMPLEMENTED] / [NOT VERIFIED]` | `recent_change`, `stale`, `unknown_timestamp`, `unknown_price` نمایش داده می‌شوند؛ هیچ‌کدام تأیید موجودی زنده نیستند. |
| Frontend جست‌وجو و مقایسه آفرها | `[IMPLEMENTED] / [NOT VERIFIED]` | UI فارسی/RTL، debounce، TanStack Query، AbortSignal، بودجه، فیلتر اعتباری، مرتب‌سازی، صفحه‌بندی، وضعیت خطا/خالی و بازکردن آفرهای واجد شرایط هر محصول نوشته شده‌اند. |
| بررسی ایستای Python | `[VERIFIED]` | `python -m compileall -q backend scripts` موفق شد. |
| بررسی ایستای TypeScript | `[VERIFIED]` | همه فایل‌های TS/TSX، شامل MissionPanel و mission-api، با TypeScript `transpileModule` بدون خطای syntax تجزیه شدند. typecheck کامل به علت نبود React/Lucide/TanStack Query نصب‌شده قابل اجرا نبود. |
| package-lock و npm | `[BLOCKED]` | رجیستری npm به علت خطای DNS در دسترس نبود؛ `package-lock.json` وجود ندارد و build/lint/test کامل فرانت‌اند اجرا نشده است. |
| Django / pytest | `[BLOCKED]` | Django نصب نیست؛ جمع‌آوری تست‌ها با `ModuleNotFoundError: django` متوقف شد. نصب dependency از PyPI هم به علت DNS ناموفق بود. |
| Docker/Compose runtime | `[NOT VERIFIED]` | فایل‌های Dockerfile/Compose/Nginx نوشته شده‌اند، اما Docker CLI در محیط سازنده نصب نیست و build/up انجام نشده است. |
| Mission API / persistence / events | `[IMPLEMENTED] / [NOT VERIFIED]` | مدل‌های PurchaseMission, MissionEvent و APIهای create/get/turn نوشته شده‌اند؛ تست runtime و migration هنوز در محیط وابستگی‌دار اجرا نشده‌اند. |
| LangGraph mission pipeline | `[IMPLEMENTED] / [NOT VERIFIED]` | گراف `parse_request → search_catalog → render_results` با adapter اختیاری LLM و fallback heuristic در `apps/agent/graph.py` و `apps/agent/llm.py` پیاده شده؛ runtime مدل واقعی تأیید نشده است. فراخوانی مدل پیش از قفل ردیف مأموریت انجام می‌شود. |
| تماس شبیه‌سازی‌شده و جایگزین | `[IMPLEMENTED] / [NOT VERIFIED]` | outcome سمت سرور، `ContactAttempt`، حفظ شروط سخت، آفر جایگزین همان محصول و محصولات جانشین هم‌دسته پیاده شده‌اند؛ هیچ تماس واقعی انجام نمی‌شود. |
| Generative UI mission panel | `[IMPLEMENTED] / [NOT VERIFIED]` | رابط Chat-first با تاریخچهٔ رویدادها در پیام مربوط، quick prompt، فرم‌های داخل گفتگو، radioهای کارت‌مانند، اعتبارسنجی عددی فارسی/عربی/انگلیسی، نتیجه/حالت خالی، مقایسهٔ حداکثر سه محصول، فهرست آفرهای هر محصول، فاصلهٔ مستقیم، لینک نقطهٔ نقشه و شبیه‌ساز استعلام؛ بازیابی از snapshot نوشته شده، اما build و مرورگر کامل به دلیل نبود بسته‌های npm تأیید نشده‌اند. |
| دیپلوی عملیاتی | `[NOT DONE]` | نسخه آنلاین و smoke test محیط عملیاتی تأیید نشده‌اند. |

## آخرین بازبینی UX/UI (2026-10-22)

- `docs/conversational-ux-research.fa.md` الگوهای ChatGPT Shopping Research، Google AI Mode Shopping، Amazon Alexa for Shopping و راهنمای UI را به تصمیم‌های این محصول پیوند می‌دهد.
- `docs/ui-quality-review.fa.md` معیارهای پذیرش برای RTL، موبایل، کنتراست، فوکوس، وضعیت‌های خطا/خالی و سناریوهای دمو را فهرست می‌کند.
- `frontend/src/styles-polish.css` خوانایی اطلاعات محصول/فروشگاه را در عرض کم بهبود می‌دهد، حداقل اندازهٔ تعامل‌های اصلی را تثبیت می‌کند و برای reduced motion و forced-colors قواعد دارد.
- `GenUIRenderer.tsx` اکنون برای فیلدهای `radio` از گزینه‌های قابل انتخاب واقعی استفاده می‌کند و ورودی عددی را به شکل text + numeric input mode می‌گیرد تا ارقام فارسی/عربی در فرم قابل واردکردن باشند؛ تبدیل و اعتبارسنجی سمت مأموریت باقی می‌ماند.
- بررسی استاتیک همین نسخه: CSS (۲ فایل) بدون خطای parse، TS/TSX (۱۳ فایل) بدون خطای نحوی، `python -m compileall -q backend scripts` موفق. این‌ها جایگزین typecheck، lint، تست واحد یا build مرورگر نیستند.

## بررسی‌های واقعاً اجراشده در آخرین مرور

| بررسی | نتیجه |
|---|---|
| `python -m compileall -q backend scripts` | موفق |
| `python scripts/verify_scaffold.py` | موفق؛ 21 مسیر ضروری موجود و 20 dependency مستقیم فرانت‌اند pin شده‌اند |
| آزمون مستقل `apps/agent/llm.py` با HTTP response ساختگی | موفق؛ schema validation و سازگاری payload بررسی شد، نه provider واقعی |
| JSON مربوط به `frontend/package.json` | معتبر |
| آزمون مستقل schema adapter LLM با تنظیمات و HTTP response ساختگی | موفق؛ اعتبارسنجی payload تست شد، نه provider واقعی |
| YAML مربوط به `compose.yaml` | parse موفق؛ سرویس‌های db/backend/frontend وجود دارند |
| بررسی line length در Python | در این نسخه Ruff در محیط نصب نیست؛ چند خط بلند وجود دارد و `ruff check .` باید در محیط توسعه اجرا شود |
| parse نحوی TS/TSX با TypeScript compiler API | موفق برای همه فایل‌های `frontend/src` |
| `tsc --noEmit --strict ... frontend/src/features/search/catalog-api.ts` | موفق برای فایل API client |
| ESLint config syntax | موفق |
| Django check و pytest | قابل اجرا نبود: dependency Django نصب نیست |
| npm lint/typecheck/test/build کامل | اجرا نشده: dependencies و lockfile در دسترس نیستند |
| Docker build/up | اجرا نشده: Docker CLI موجود نیست |

## Gateهای لازم پیش از اعلام آمادگی دمو

از `backend/` در محیط دارای dependencies و PostgreSQL اجرا کنید:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate
pytest -q
ruff check .
ruff format --check .
python manage.py import_dataset --archive ../data/starcoach-dataset-v16-cap300-csv.zip --dry-run
python manage.py import_dataset --archive ../data/starcoach-dataset-v16-cap300-csv.zip
```

از `frontend/` پس از ایجاد و commit کردن lockfile در محیط دارای دسترسی npm:

```bash
npm ci
npm run lint
npm run typecheck
npm test
npm run build
```

در نهایت `docker compose config`, `docker compose build`, اجرای سرویس‌ها و smoke test endpointها را اجرا کنید. تا سبزشدن این gateها، محصول runtime-verified نیست.


## Sprint 2 — مأموریت عامل و بازیابی تماس

| قابلیت | وضعیت فعلی | فایل‌های اصلی |
|---|---|---|
| ذخیره مأموریت و event sequence | کد نوشته شده؛ runtime تست نشده | `apps/missions/models.py`, `services.py`, `views.py`, `migrations/0001_initial.py` |
| API مأموریت | کد نوشته شده | `POST /api/v1/missions/`, `GET /api/v1/missions/{id}/`, `POST /api/v1/missions/{id}/turns/` |
| SSE event envelope | کد نوشته شده؛ فرانت‌به‌بک‌اند اجرا نشده | `apps/missions/views.py`, `features/missions/mission-api.ts` |
| LangGraph + optional LLM adapter | adapter سازگار با OpenAI اضافه شده؛ نیازمند API key/model و runtime test | `apps/agent/graph.py`, `apps/agent/llm.py`, `requirements.txt` |
| تماس کنترل‌شده | outcomeهای server-owned با ترتیب قابل‌تکرار هر مأموریت | `apps/agent/simulator.py`, `apps/missions/views.py` |
| بازیابی بعد از شکست | آفرهای همان محصول و محصولات جانشین هم‌دسته، با اعمال دوباره شروط خرید | `apps/missions/views.py`, `apps/agent/simulator.py` |
| UI مأموریت | رابط فارسی/RTL، نتایج عامل و دکمه بررسی موجودی دمو | `frontend/src/features/missions/MissionPanel.tsx` |
| تست‌های اضافه‌شده | source موجود؛ اجرای pytest مسدود به نبود Django | `apps/missions/tests.py`, `apps/agent/tests.py` |

**محدودیت مهم:** اگر `LLM_API_KEY` یا `LLM_MODEL` تنظیم نشود، parser قطعی استفاده می‌شود. adapter مدل نوشته شده اما اتصال به provider واقعی و رفتار آن در runtime هنوز آزمایش نشده است؛ مسیر جست‌وجو و فیلترها باید مستقل از LLM باقی بماند.


## راستی‌آزمایی محیط توسعه و ممیزی منبع (2026-10-21)

- `scripts/audit_dataset.py` با Python standard library روی ZIP واقعی اجرا شد و snapshot در `docs/dataset-audit-snapshot.fa.md` ثبت شد.
- نتیجه ممیزی ماشینی: products=225,903، shops=6,476، offers=331,506؛ شناسه‌های تکراری/خالی صفر، آفرهای دارای product/shop یتیم صفر و JSONهای ساختاری نامعتبر صفر در ستون‌های بررسی‌شده.
- 15,083 آفر قیمت خالی، 144 قیمت بالاتر از آستانه کیفی 100 میلیارد تومان، و 769 timestamp خالی دارد؛ هیچ‌یک از این آمار دلالت بر موجودی زنده نمی‌کند.
- اسکریپت راه‌اندازی/تست Windows در `scripts/verify-local.ps1` ساخته شده است. آن را روی ماشین دارای Python 3.13، Node 22.12+ و دسترسی package registry اجرا کنید.
- در محیط فعلی، Django/DRF/LangGraph نصب نیستند، Docker CLI موجود نیست و `registry.npmjs.org` با خطای DNS resolve نشد؛ بنابراین `manage.py check`, pytest, npm install/typecheck/test/build, Docker build/up و import واقعی PostgreSQL هنوز runtime-verified نیستند.
- برای خروج از این وضعیت، `docs/windows-setup-and-verification.fa.md` را دنبال کنید و اولین failure کاملِ اسکریپت را برگردانید؛ secrets را ارسال نکنید.


## پیگیری خطای Ruff از اجرای Windows (2026-10-22)

کاربر پس از اجرای `scripts/verify-local.ps1` گزارش داد که system check Django موفق، migration/model consistency بدون تغییر و تست‌های بک‌اند با 48 تست موفق بوده‌اند، اما Ruff با 9 مورد خطا متوقف شده است. اصلاح‌ها در نسخه فعلی:

- `backend/apps/agent/graph.py`: موارد تکراری `STOP_WORDS` حذف و گونه‌های نوشتاری یکتای فارسی حفظ شدند.
- `backend/apps/missions/services.py`: import استفاده‌نشده `django.db.transaction` حذف شد.
- `backend/config/settings/local.py`: تنظیمات پایه از طریق `base_settings` ارجاع داده می‌شوند تا F405 از ارجاع‌های ناشی از wildcard import رفع شود؛ wildcard import لازم برای الگوی Django حفظ شده و F403 روی همان خط نادیده گرفته شده است.

این سه تغییر مطابق خروجی Ruff گزارش‌شده انجام شده‌اند. پس از جایگزین‌کردن فایل‌ها، کاربر باید مجدداً `python -m ruff check .` را داخل `backend` یا کل `scripts/verify-local.ps1` را از ریشه اجرا کند. اجرای Ruff پس از اصلاح در محیط ساخت این بسته ممکن نبود چون Ruff در آن محیط نصب نیست؛ تأیید نهایی با اجرای محلی باقی می‌ماند.

## آخرین تغییر: دامنه‌گذاری عبارت «فشارسنج»

- [x] شناسایی ابهام مشاهده‌شده میان فشارسنج پزشکی و فشارسنج محیطی/صنعتی.
- [x] دامنه‌گذاری قابل توضیح در بک‌اند برای عبارت عمومی و عبارت‌های صریح پزشکی/صنعتی.
- [x] اضافه‌شدن `intent_hint` به پاسخ API برای نمایش گزینه جایگزین در UI.
- [x] اضافه‌شدن تست‌های API برای عبارت عمومی، عبارت صنعتی و جست‌وجوی برند/مدل مشخص.
- [ ] اجرای تست‌های جدید Django روی محیط توسعه کاربر.
- [ ] اجرای typecheck/lint/build فرانت‌اند روی محیط توسعه کاربر.
- [ ] آزمون دستی عبارت `فشارسنج` و دکمه تغییر به `فشارسنج صنعتی` در مرورگر.

محدودیت: این قانون تنها برای مسئله فشارسنج اضافه شده و جایگزین موتور معنایی عمومی نیست.

## به‌روزرسانی Generative UI

- [x] رندرر ثبت‌شده و امن برای کامپوننت‌های رابط دریافت‌شده از رویداد `ui.component`.
- [x] `clarification_form` برای درخواست فاقد محصول و `empty_state` همراه با فرم اصلاح عبارت/شرایط.
- [x] `component_stack` برای چیدن چند قطعه UI مرتبط در یک پاسخ؛ شامل انتخاب دامنه برای عبارت‌های مبهم کاتالوگ.
- [x] رندرر عمومی برای جدول مقایسه، وضعیت استعلام و برنامه مراجعه؛ فهرست محصول از رندرر تخصصی موجود استفاده می‌کند.
- [x] برنامه مراجعه در نتیجه تأییدشده simulator؛ منبع شبیه‌سازی و عدم انجام تماس واقعی آشکار است.
- [x] امکان پاک‌کردن سقف بودجه با `max_price_toman: null`.
- [x] تست‌های قراردادی backend و frontend اضافه شده‌اند.
- [ ] اجرای مجدد lint، typecheck و suite آزمون‌ها در محیط توسعه پروژه پس از دریافت این تغییرات؛ وابستگی‌های npm در محیط تولید فایل این بسته قابل نصب نبودند.



## Chat-first UX و پژوهش Generative UI — 2026-10-22

- [x] بررسی منابع رسمی تجربه‌های خرید مکالمه‌ای: ChatGPT Shopping Research، Google AI Mode Shopping، Amazon Alexa for Shopping و Perplexity Shopping. تصمیم‌های پروژه در `docs/conversational-ux-research.fa.md` با منابع و محدودیت‌های قابل‌اقتباس ثبت شده است.
- [x] رابط ورود به‌صورت چت است، نه صفحهٔ فهرست فروشگاهی؛ quick promptها راهنمای شروع‌اند و تایپ اجباری نیست.
- [x] پیام کاربر، پاسخ دستیار و UI هر پاسخ در transcript جداگانه نمایش داده می‌شوند؛ برای پیام‌های قبلی عملیات تازه/ویرایش نتایج فعال نیست.
- [x] تغییر شروط، تکمیل اطلاعات، تغییر دامنه و مقایسه در قالب componentهای ساختاریافته درون گفتگو انجام می‌شوند.
- [x] برچسب کیفیت قیمت، timestamp دقیق/نسبی و فاصلهٔ مستقیم در کارت نتایج اضافه شده‌اند؛ فاصله زمان رانندگی نیست و لینک OSM فقط نقطهٔ ثبت‌شده را باز می‌کند.
- [x] تست واحد برای helperهای زمان/قیمت و مختصات نقشه اضافه شده؛ 8 assertion از helperهای transpileشده به‌صورت smoke check مستقل اجرا شدند.
- [x] parse نحوی 13 فایل TS/TSX، بررسی importهای CSS، TypeScript strict برای `ui-formatters.ts`، `python -m compileall -q backend scripts` و `scripts/verify_scaffold.py` موفق شدند.
- [ ] `npm run lint`, `npm run typecheck`, `npm test`, `npm run build`, Django `pytest` و Docker smoke test برای نسخهٔ نهایی هنوز اجرا/تأیید نشده‌اند: نصب npm در محیط تولیدکننده timeout شد، Django نصب نیست و Docker CLI وجود ندارد.
