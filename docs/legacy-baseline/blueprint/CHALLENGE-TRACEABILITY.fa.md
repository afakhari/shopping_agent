# ردیابی رسمی الزامات چالش به قابلیت و آزمون

**مبنای نیاز:** متن رسمی و رونوشت ویدئو که توسط شرکت‌کننده ارائه شده است. ویدئوی اصلی مستقلاً مشاهده نشده است. معیارهای امتیازی عیناً از شرح چالش آمده‌اند؛ تست‌های معرفی‌شده تصمیم مهندسی ما هستند.

| Req ID | الزام برگزارکننده | پوشش طراحی | آزمون پذیرش | امتیاز مرتبط |
|---|---|---|---|---|
| R01 | کشف مدل مناسب برای نیاز مبهم | Intent → retrieval → comparison | E02 | محصول، هوشمندی |
| R02 | مقایسه محصول و قیمت | ProductComparison و OfferComparison | E01/E02 | محصول، UX |
| R03 | فروشگاه دارای آفر کالا پیدا شود | Product→Offer→Shop قطعی | E01 | محصول، دیتاست |
| R04 | انتخاب محدوده و نزدیکی | Geo filters و map/list | E06/E13 | محصول، UX |
| R05 | مقایسه قیمت، فاصله، ساعت | ShopExplorer و VisitHoursService | E01/E10 | محصول، UX |
| R06 | تعامل با فروشنده | ContactProvider و approval | E08/E09 | هوشمندی |
| R07 | قیمت و موجودی استعلام شوند | ContactAttempt provenance | E07/E08/E09 | هوشمندی، دیتاست |
| R08 | فروشنده جواب نمی‌دهد | recovery no_answer | E08 | هوشمندی |
| R09 | جایگزین در صورت اتمام موجودی | recovery unavailable | E08 با fixture ناموجود | هوشمندی |
| R10 | فروشگاه بسته است | hours/closed recovery | E10 | محصول، هوشمندی |
| R11 | آدرس پاساژ/طبقه/واحد | AddressHintExtractor با provenance | E11 | محصول |
| R12 | فقط پذیرندگان اعتباری | Offer-level credit rules | E04 | محصول، دیتاست |
| R13 | مرز بودجه و شرایط قابل تغییر | Constraint chips + sheet | E03/E05 | UX |
| R14 | RTL و موبایل | layout tokens و a11y | mobile QA | UX |
| R15 | تفاوت قیمت ثبت‌شده، زمان و موجودی | data provenance | E07/E09 | دیتاست |
| R16 | حالات نامعلوم شفاف | tri-state labels | E07/E10 | دیتاست، UX |
| R17 | پایداری و استقرار | Docker + CI + readiness | production smoke | دیپلوی |
| R18 | نمایش واقعی ارزش محصول در دمو | golden journey و script | ۵ دقیقه ویدئو | محصول، UX |
| R19 | فنی قابل اتکا | contract tests + security | CI gate | فنی |
| R20 | استفاده از دیتاست رسمی | checksum/import/integrity | import smoke | دیتاست |

## وزن‌های رسمی

| حوزه | امتیاز |
|---|---:|
| محصول | ۷۵ |
| تجربه کاربری | ۷۵ |
| هوشمندی | ۵۰ |
| دیپلوی | ۴۰ |
| مهندسی | ۴۰ |
| دیتاست | ۲۰ |
| **جمع** | **۳۰۰** |

## تحقق و پوشش

ستون «پوشش طراحی» به معنی *planned* است، نه عملیاتی‌شدن. پیاده‌سازی زمانی پذیرفته است که تست و شواهد URL واقعی در `docs/blueprint/RELEASE-CHECKLIST.fa.md` ثبت شود. وضعیت کد موجود در `docs/implementation-status.fa.md` فقط snapshot تاریخی آن نسخه است.
