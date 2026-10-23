# آمادگی پیش از پیاده‌سازی مرحله بعدی بازارکامپس | ۲۳ اکتبر ۲۰۲۶

**وضعیت:** تحقیق و طراحی پیش از اتصال نشان، نه پیاده‌سازی سرویس نقشه. مبنای به‌روز `main@e796d7a5aa96` شامل PRهای #26، #28 و #29 است. هدف پروژه منحصراً کمک به **خرید حضوری از فروشگاه‌های تهران** است. مرجع دامنه چالش و چهار گام آن: `شرح-پروژه.txt` کاربر و متن ویدئوی چالش؛ ویدئوی مستقل مشاهده نشده و فقط متن ارائه‌شده مطالعه شده است.

> **مرز شواهد:** گیت‌های ۵/۵ PRهای #26، #28 و #29 بر fixture مصنوعی موفق بودند؛ استقرار عمومی، ETA معتبر، ارتباط واقعی با فروشنده، ۵۰ gold query، ۱۲ E2E واقعی و usability testing کامل هنوز اثبات نشده‌اند. بخش‌هایی از اسناد تاریخی `CURRENT-STATUS` و `ROADMAP` مربوط به قبل از این PRها هستند؛ اطلاعیه به‌روزرسانی در صدر آن‌ها اضافه شده است. مستند بودن یک ویژگی به معنای پیاده شدن آن نیست.

## نتیجهٔ ممیزی ZIP اصلی به‌صورت کامل

منبع: `starcoach-dataset-v16-cap300-csv.zip`، پیمایش کامل CSVها، بدون تماس با ارائه‌دهنده بیرونی؛ زمان سنجش تازگی: ۲۳ اکتبر ۲۰۲۶ UTC.

| سنجه | نتیجه | الزام تجربهٔ کاربر |
|---|---:|---|
| Products/Shops/Offers | 225903 / 6476 / 331506 | موجودی واقعی معلوم نیست |
| Shops دارای حداقل Offer | 3792 (58.55% Shops) | فروشندهٔ همان محصول فقط با **Offer موجود** |
| مختصات معتبر و در box پروژه | 6476 (100%) | نقطهٔ ثبت‌شده ≠ مسیر/ETA تأییدشده |
| ساعات هفتگی غیرخالی | 4473 (69.07%) | «طبق برنامه ثبت‌شده»، unknown صریح |
| محصول با brand | 57634 (25.51%) | فیلتر brand صریح، نه استنتاج اجباری |
| محصول با model مستقل | 4056 (1.80%) | title/spec-first؛ مدل دقیق control اختیاری |
| Specs غیرخالی | 144599 (64.01%) | مقایسه تفاوت واقعی، unknown صریح |
| تصاویر غیرخالی | 224684 (99.46%) | کارت تصویری و fallback |
| Offer بدون قیمت معتبر | 15083 (4.55%) | هرگز صفرِ ساختگی |
| Offer با آخرین تغییر قیمت بالای ۳۰ روز | 169585 (51.16%) | هشدار تاریخی بودن قیمت؛ میانهٔ سن 31.4 روز |
| Shops با گزینه credit حضوری ثبت‌شده | 82 (1.27%) | hard constraint در سطح Offer |
| برچسب مکان فردوسی و شیخ هادی | 3282 و 1587 (75.18% فروشگاه‌ها) | نمایش محدودیت پوشش جغرافیایی تهران |

طبق متن صریح چالش، ۶۳۶۴ نام Shop و تمام شماره تلفن‌ها **ساختگی** هستند؛ وجود contact row به معنای قابلیت تماس واقعی نیست. فروشگاه‌های دیگر یا در سایر بخش‌های تهران نباید به کاربر به‌عنوان covered تلقی شوند. قیمت‌های با timestamp معتبر تقریباً همگی در تاریخ ممیزی بیش از یک هفته از آخرین تغییرشان گذشته‌اند؛ عبارت «قیمت امروز» مجاز نیست.

## انتخاب از الگوهای رقبا

- **Google Maps**: لیست و نقشه با selection هماهنگ، نه کپی پایگاه عمومی مکان‌ها برای نمایش shops بدون Offer.
- **Baymard**: خلاصهٔ فیلترهای فعال، فهرست محصول قابل اسکن و مقایسهٔ دسکتاپ spec-driven. پژوهش دربارهٔ **استفادهٔ اندک از ابزار مقایسه در موبایل** می‌گوید به‌جای پیش‌فرض قراردادن جدول عریض، روی کارت‌های تفاوت‌محور و list quality تمرکز شود.
- **IKEA/Google Shopping**: راهنمایی قبل از مراجعه و محصول‌یابی محاوره‌ای، نه انتقال checkout یا تأیید موجودی بدون شواهد.
- **نشان / MapLibre SDK رسمی**: ارائه‌دهنده مشروط منتخب برای rendering نقشه، در انتظار کلید وب، quota، Terms و تأیید دسترسی شبکه. به [ADR نشان](NESHAN-INTEGRATION-ADR-2026-10-23.fa.md) مراجعه کنید. برای نسخهٔ اول، ۸ تا ۲۴ Offer موجود را از همان endpoint فهرست نشان دهد، با لیست مستقل در شکست نقشه. از OSMF tile.openstreetmap.org به‌عنوان زیرساخت مقیاس‌پذیر با SLA فرضی استفاده نشود.
- **AG-UI**: در حال حاضر مهاجرت از SSE+snapshot موجود لازم نیست؛ component schema و حفظ نسخه state اولویت دارند.

## تصمیم طراحی

**Adaptive In-Person Shopping Workspace** حفظ می‌شود: گفتگو و یک سطح اصلی متناسب با intent و stage، موبایل یک‌ستونه و list-first، دسکتاپ گفتگو+فضای تصمیم، user may jump stages. اصل `every message → intent + reference + hard filters + evidence → reply + optional allowlisted UI`.

رفتارهای کلیدی:
1. «سلام» text-only، صفر Search/LLM؛ «سلام هدفون می‌خوام» خرید واقعی.
2. «تا چهار میلیون گوشی می‌خوام» پس از لپ‌تاپ = محصول جدید، نه refine لپ‌تاپ.
3. «دومی» فقط از focus/ordered IDs و result_set_id فعال؛ مبهم = یک clarification.
4. «این دو تا چه فرقی دارند» = component مقایسهٔ difference-first و unknown.
5. «فروشنده دوم امشب بازه؟» = Shop/Offer ID ثبت‌شده، timezone Tehran، نه ادعای باز بودن واقعی.
6. «موجودی رو بررسی کن» = نیازمند اقدام تأییدی، `demo_simulation` و source labels.
7. «فروشنده جواب نداد» = user_report، پیشنهاد **همان محصول** با همان hard filters، بدون ادعای تماس.
8. پیام حین SSE = صف دیدنی قابل حذف؛ در 502 نامطمئن متوقف تا خواندن snapshot.
9. تغییر شرایط = version invalidate برای card/plan؛ نتیجه دیررس نمی‌تواند panel جدید را override کند.
10. نقشه ناموفق = فهرست و نشانی و لینک نقطه همیشه کار کند، حتی وقتی Tile/ETA اصلاً فعال نیست.

## قرارداد اجرای برش بعدی

**Slice A — Correct Conversation:** `apps/agent/contextual.py` + `missions/views.py`؛ planner چندنیتی schema-bound و `mission_version/expected_version` برای race. معیار: ≥۹۵٪ intent/action در corpus داوری انسانی، صفر action اثرگذار اشتباه؛ سنجه هدف است نه نتیجه فعلی.

**Slice B — Controlled GenUI:** `genui-types.ts`, `GenUIRenderer.tsx`؛ discriminated component schema، payload validation، status/provenance، replace/update/supersede. معیار: هیچ `schema_invalid_render` یا card منسوخِ قابل اقدام نباشد.

**Slice C — State UX:** `MissionPanel.tsx`, `mission-api.ts`؛ refactor تدریجی state/reducer، snapshot source of truth، queue and idempotent replay، selected Offer پایدار میان map/list.

**Slice D — Map/list:** برش فعلی #29 پیش‌نمایش موقعیت فروشنده منتخب و انتخاب همگام فهرست را ارائه کرده؛ نقشه چندپین با نشان هنوز اضافه نشده است. `shop-map.ts` و Map UI جدید؛ یک فهرست اصلی source-ID، pin sync، region + explicit geolocation consent، no-map fallback و lazy load. Tile provider باید Terms/Quota/CSP/RTL را در آزمایش ۳۹۰px بگذراند.

**Slice E — Route/ETA (deferred until proof):** انتخاب مشروط نشان طبق [ADR](NESHAN-INTEGRATION-ADR-2026-10-23.fa.md)، بدون کلید/قرارداد قطعی. آداپتور مستقل backend (timeouts، cache، quotas، top 3-5 selected shops). Endpoint پیشنهادی `POST /api/v1/route-estimates/` تنها بعد از اعتبارسنجی کلید و پوشش تهران. duration از API معتبر؛ هرگز از Haversine تخمین زده نشود.

**Slice F — Search Evaluation:** ۵۰ query کاندید از دسته/عنوان/برند/مدل واقعی استخراج شده‌اند اما `unverified_seed` اند؛ داوری انسانی relevance و gold products قبل از Recall@10/MRR@10، benchmark سخت‌گیری brand/model/credit و latency p95.

**Slice G — Production:** HTTPS، secret/rate/quotas BoxAPI، mission session auth/CSRF/CORS، CSP tiles، anonymized logs، health، real ZIP smoke، ۱۲ E2E مستقل، ۲۰ edge و ویدئوی ۵ دقیقه از محیط منتشرشده.

## آزمون پذیرش قابل اجرا

**۲۰ مورد لبه‌ای:** E01 مدل دقیق؛ E02 نیاز کاربردی؛ E03 ambiguity؛ E04 صفر نتیجه؛ E05 بودجه؛ E06 اعتبار؛ E07 قیمت نامعلوم؛ E08 shop بدون Offer؛ E09 ساعات unknown/overnight؛ E10 تماس دمو موفق؛ E11 no_answer→backup؛ E12 price_changed/budget؛ E13 unavailable؛ E14 تفاوت warranty؛ E15 تغییر فیلتر وسط SSE؛ E16 قطع شبکه/refresh؛ E17 geolocation denied؛ E18 tile fallback؛ E19 پاساژ بدون واحد/طبقه؛ E20 idempotent retry.

**۱۲ سفر مستقل:** J01 نیاز→مدل، J02 title دقیق، J03 بودجه+اعتبار، J04 مقایسه، J05 same-product shops، J06 list↔map selection، J07 منطقه دستی، J08 ساعات/پاساژ، J09 تماس آزمایشی و plan، J10 فروشنده بی‌پاسخ و جایگزین، J11 price_changed/unavailable، J12 SSE/refresh/idempotency. هر مورد به screenshot 320/360/390/1440، نتیجه API و ردیابی provenance نیاز دارد. تا اجرای واقعی باید `NOT_RUN` باقی بماند.

**اولویت داوری:** Product 75 + UX 75 + Intelligence 50 بالاتر از افزودن زیرساخت‌های غیرضروری است. ادعای کامل بودن تا اجرای user testing، data golden و public deploy ممنوع.

## ریسک‌ها و شروط ورود به اجرا

| Gate | مانع فعلی | تصمیم |
|---|---|---|
| DataTruth | نام/شماره ساختگی و قیمت تاریخی | طراحی provenance و no-live-availability اجباری |
| MapLegal | Provider/Tiles licence/Key بدون تست | MapLibre renderer مشروط؛ لیست fallback همیشه |
| GeoCoverage | برچسب‌های فردوسی و شیخ هادی غالب‌اند | اطلاع‌رسانی پوشش؛ عدم جعل seller نزدیک |
| LLMQuality | BoxAPI صرفاً intent تست‌شده | multi-intent bench پیش از بزرگ کردن graph |
| UIQuality | کاربر واقعی و axe/keyboard کامل نشده | pilot حداقل ۵ تا ۱۰ کاربر؛ ۲۰ edge/۱۲ E2E |
| Release | URL عمومی HTTPS و budget/quotas تأیید نشده | هیچ ادعای Production-ready |

## سیاست هزینه CI

**این برش صرفاً docs + dataset audit است و نباید CI مصرف کند.** در کدنویسی آینده یک PR تجمیعی Draft و تست موضعی؛ یک `quality-gates` نهایی روی آخرین SHA پایدار پیش از merge. اجرای مدل/نقشه فقط با بودجه/کلید خصوصی و کنترل سقف مصرف.

## منابع تحقیقات

- https://baymard.com/research/ecommerce-product-lists
- https://baymard.com/research-articles/provide-comparison-features
- https://baymard.com/mcommerce-usability/benchmark/mobile-page-types/filtering-options
- https://maplibre.org/maplibre-gl-js/docs/
- https://operations.osmfoundation.org/policies/tiles/
- https://www.w3.org/TR/wcag/
- https://ag-ui.ai/en/technologies/ag-ui

پیوست‌های تحلیل در بستهٔ گفتگو: `BazaarCompass-Dataset-Preimplementation-Profile-2026-10-23.json`، `BazaarCompass-50-Query-Candidates-NOT-GOLD.csv`، `BazaarCompass-Scenario-Fixture-Seeds-2026-10-23.json`، `BazaarCompass-12-Journeys-20-Edges-Plan.json` و نسخهٔ مفصل سند پیش از پیاده‌سازی.


## وضعیت PR #27

این تحقیق از PR تاریخی Draft #27 پالایش و در یک commit فقط مستنداتی روی main ثبت شد. متن PR #27 با تغییرات قدیمی وضعیت پروژه همپوشانی داشت؛ برای عدم راه‌اندازی CI پنج‌مرحله‌ای به خاطر docs و جلوگیری از تعارض تاریخچه، PR #27 به‌عنوان superseded بسته می‌شود. برچسب‌های Gold هنوز انسانی تأیید نشده‌اند.
