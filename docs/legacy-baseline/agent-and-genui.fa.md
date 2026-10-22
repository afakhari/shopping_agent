# قرارداد عامل، LangGraph و Generative UI

**وضعیت:** گراف کوچک MVP پیاده شده است؛ `apps/agent/graph.py` مسیر `parse_request → search_catalog → render_results` را دارد و `apps/agent/simulator.py` ابزار تماس کنترل‌شده را اجرا می‌کند. استخراج intent اختیاری از API سازگار با OpenAI در `apps/agent/llm.py` پیاده شده است؛ runtime آن هنوز به دلیل محدودیت dependencies/provider در این محیط تأیید نشده است.

## 1. هدف و مرز مسئولیت

عامل مسئول فهم قصد، تشخیص اطلاعات ناقص، انتخاب ابزار بعدی و توضیح پیشنهاد است. منبع حقیقت و محاسبه دقیق در ابزارهای پایتون/Django قرار دارد. مدل اجازه ندارد SQL دلخواه اجرا کند یا واقعیت‌هایی مانند قیمت و موجودی را حدس بزند.

یک graph مرکزی کافی است. چند عامل مستقل، vector store و سرویس orchestration جدا برای نسخه اول ضروری نیستند.

## 2. State پیشنهادی

```python
class MissionState(TypedDict):
    mission_id: str
    user_message: str
    parsed_intent: dict
    hard_constraints: dict
    soft_preferences: dict
    missing_required_fields: list[str]
    candidate_product_ids: list[str]
    selected_product_ids: list[str]
    eligible_offer_ids: list[str]
    excluded_reason_counts: dict[str, int]
    contact_attempt_ids: list[str]
    alternative_offer_ids: list[str]
    current_stage: str
    last_error_code: str | None
    ui_events: list[dict]
```

این نمونه قرارداد منطقی است؛ نوع دقیق باید پس از پیاده‌سازی با `TypedDict`/Pydantic تعریف شود. در state، داده‌های بزرگ محصول یا تصویر را در صورت امکان با ID نگه دارید؛ تمام دیتاست یا transcript کامل را به هر prompt ندهید.

## 3. Hard constraints و preferences

نمونه `hard_constraints`:

```json
{
  "city": "tehran",
  "max_price_toman": "30000000",
  "must_have_in_person_credit": true,
  "origin": null,
  "radius_m": null,
  "required_specs": {}
}
```

قواعد:

- شروطی که کاربر با «حتماً»، «فقط»، «بیشتر از این نشود» یا معنای مشابه اعلام می‌کند، سخت‌اند.
- اولویت‌هایی مانند «ترجیحاً نزدیک‌تر» نرم‌اند مگر کاربر شعاع/حد تعیین کند.
- مدل می‌تواند درباره مقدار گمشده سؤال کند؛ نباید شرط hard را خودکار به preference تبدیل کند.
- مجموعه فعلی تنها داده تهران دارد. اگر شهر دیگری صریحاً درخواست شد، نباید تهران را به‌عنوان نتیجه آن شهر بازگرداند.

## 4. گراف هدف

Nodeها:

1. `parse_request`: استخراج intent/constraints به schema.
2. `check_clarification`: اگر ابهام روی جست‌وجو یا eligibility اثر دارد، سؤال بساز.
3. `search_catalog`: ابزار قطعی جست‌وجو.
4. `apply_eligibility`: ابزار/سرویس قطعی فیلتر hard constraints.
5. `rank_candidates`: رتبه‌بندی گزینه‌های واجد شرایط.
6. `render_candidates`: emit محصول/مقایسه/فروشگاه از داده tool outputs.
7. `decide_verification`: آیا کاربر درخواست بررسی کرده یا قیمت/موجودی آنقدر مهم است که اقدام پیشنهاد شود؟ برای دمو با سیاست روشن.
8. `contact_simulator`: فقط پس از اقدام مجاز؛ نتیجه از server fixture.
9. `evaluate_contact`: اگر no-answer/unavailable/closed/error، مسیر بازیابی.
10. `find_alternatives`: جست‌وجوی مجدد با تمام hard constraints حفظ‌شده.
11. `build_purchase_plan`: خروجی نهایی مراجعه.
12. `finish_or_ask`: تمام یا سؤال انتخابی بعدی.

مسیر کوتاه برای درخواست مشخص: parse → search/eligibility → rank → render. فیلترهای UI نباید این graph را دوباره اجرا کنند.

## 5. ابزارهای مجاز

| Tool | Input | Output | اثر جانبی |
|---|---|---|---|
| `search_products` | query + candidate filters | product IDs + matched fields | خیر |
| `get_product_details` | product IDs | structured product/specs/images | خیر |
| `find_eligible_offers` | product ID + constraints | eligible offers/shop subset + exclusion counts | خیر |
| `compare_offers` | offer IDs + preferences | normalized comparison facts + reasons | خیر |
| `get_shop_details` | shop IDs | address, hours, payment, contact fields | خیر |
| `calculate_distance` | origin + shop coordinates | direct distance; label must say straight-line | خیر |
| `get_route` | origin/destination/provider | route estimate or typed failure | external read; timeout required |
| `simulate_store_contact` | mission/shop/offer/purpose | controlled outcome and timestamp | writes ContactAttempt |
| `find_alternatives` | original constraints + exclusions | new eligible offers | خیر |
| `build_purchase_plan` | chosen candidates | plan DTO | خیر |

Tool result envelope SHOULD include `ok`, `data`, `source`, `observed_at`, `error_code` where relevant. Tool errors are typed; do not return fabricated empty success when dependency failed.

## 6. تماس شبیه‌سازی‌شده

- Mode default: `AGENT_CONTACT_MODE=DEMO_SIMULATION`.
- Outcome enum: `confirmed_available`, `unavailable`, `no_answer`, `closed`, `error`.
- Scenario outcomes are server-owned, deterministic under a scenario seed/profile, inspectable in tests and reproducible in demo.
- The client supplies shop/offer/purpose only; it must not select the outcome.
- UI labels should accurately say e.g. «نتیجه استعلام در سناریوی دمو» where relevant to evaluation, but avoid repeatedly exposing dataset caveats as customer-facing copy.
- Simulator outputs must not be logged as a real phone event. Use `source_type="demo_simulation"` internally and in event metadata.
- No external real call or message is sent in the default demo mode.

## 7. Generative UI contract

به‌جای UI آزاد، union قابل‌اعتبارسنجی تعریف شود:

```typescript
type UIComponent =
  | { type: "clarification"; title: string; question: string; options: UIOption[] }
  | { type: "product_results"; products: ProductCardDTO[] }
  | { type: "product_comparison"; products: ProductCompareDTO[]; criteria: string[] }
  | { type: "shop_results"; shops: ShopCardDTO[]; map?: MapDTO }
  | { type: "contact_progress"; attempts: ContactAttemptDTO[]; next_action?: UIAction }
  | { type: "alternative_options"; alternatives: OfferCardDTO[]; alternative_products?: ProductResultDTO[]; preserved_constraints: string[] }
  | { type: "purchase_plan"; plan: PurchasePlanDTO };
```

DTOها باید در frontend TypeScript و backend schema هم‌معنا باشند. اگر امکان اشتراک types خودکار فراهم نیست، تست contract روی نمونه JSON مشترک تعریف شود.

### قیود رندر

- `type` حتماً از allowlist باشد.
- متن و شناسه‌های دریافتی از LLM به‌تنهایی منبع قیمت/موجودی نشوند؛ داده display DTO از سرویس داخلی ساخته می‌شود.
- هیچ رشته HTML یا کد React از مدل اجرا نشود.
- تعداد کارت‌ها محدود؛ تصویرها lazy-loaded.
- تمام actionهای کاربر به endpoint مشخص و validator سمت سرور متصل شوند.
- payload بدشکل به fallback متنی/خطای کنترل‌شده تبدیل شود، نه crash کل صفحه.

## 8. Event envelope

```json
{
  "schema_version": 1,
  "mission_id": "m_example",
  "seq": 3,
  "type": "ui.component",
  "payload": {
    "component": "product_results",
    "data": {"products": []}
  }
}
```

Event typeهای اولیه:

- `stage`: مرحله جاری و متن progress کوتاه.
- `assistant.message`: متن توضیحی.
- `ui.component`: payload از union بالا.
- `tool.started` / `tool.completed` / `tool.failed`: trace قابل‌نمایش با نام انسانی‌شده، بدون آرگومان/خروجی حساس.
- `mission.snapshot`: snapshot قابل بازیابی.
- `mission.completed`: مأموریت تمام شده.
- `mission.error`: خطای امن با action بعدی.

`seq` در یک mission افزایشی است. frontend event تکراری را نادیده می‌گیرد و snapshot جدیدتر را بر قدیمی‌تر ترجیح می‌دهد.

## 9. حافظه و persistence

- `PurchaseMission` state ضروری را ذخیره کند تا refresh state را از بین نبرد.
- eventهای اصلی `MissionEvent` قابل‌خواندن باشند؛ promptهای خام و hidden reasoning در DB یا UI ذخیره/نمایش داده نشوند.
- تاریخچه پیام محدود باشد؛ state ساختاریافته بر transcript بلند ترجیح دارد.
- اگر checkpointer LangGraph برای نسخه اول اضافه شد، انتخاب backend و cleanup policy مستند شود؛ نیازی به platform hosting عامل نیست.

## 10. الگوی خطا و fallback

- LLM unavailable: جست‌وجوی مستقیم همچنان کار کند؛ پیام کوتاه و گزینه جست‌وجوی ساختاریافته نشان داده شود.
- route provider unavailable: نشانی و مختصات + link نقشه؛ هیچ ETA اختراع نشود.
- contact scenario error: وضعیت خطا و پیشنهاد استعلام بعدی/فروشگاه جایگزین.
- no eligible results: UI empty state با کنترل تغییر شرط.
- malformed model output: schema validation؛ یک retry محدود یا fallback؛ loop نامحدود ممنوع.

## 11. معیار پذیرش عامل

- در هیچ تستی شرط hard بدون action کاربر شل نشود.
- ابزارها فقط به شناسه‌های معتبر دسترسی بگیرند.
- پس از `no_answer`، graph بتواند به گزینه جایگزین برسد.
- `unavailable` به عنوان `confirmed_available` نمایش داده نشود.
- رویداد UI از داده سرور رندر شود و JSON ناقص crash ندهد.
- هر ابزار duration/result code قابل مشاهده در log داشته باشد.


## 12. وضعیت پیاده‌سازی فعلی و مرزهای آن

- گراف با `langgraph.graph.StateGraph` ساخته می‌شود، اگر dependency نصب باشد؛ در محیط حداقلی، همان node functionها به‌ترتیب اجرا می‌شوند.
- `parse_request_node` ابتدا intent extraction اختیاری را از `apps/agent/llm.py` صدا می‌زند؛ اگر کلید/مدل پیکربندی نشده یا provider timeout/error/schema نامعتبر داشته باشد، به parser heuristic محلی fallback می‌کند.
- Adapter فقط عبارت محصول، بودجه، ترجیح مرتب‌سازی و intent خرید اعتباری را استخراج می‌کند. هر خروجی schema-validate می‌شود؛ قیمت/موجودی/فروشگاه تولید نمی‌کند و جست‌وجو فقط از سرویس قطعی SQL استفاده می‌کند.
- API مأموریت، فراخوانی اختیاری مدل را پیش از گرفتن row lock انجام می‌دهد تا timeout شبکه، تراکنش دیتابیس را طولانی نکند؛ سپس محدودیت‌ها مجدداً اعتبارسنجی می‌شوند.
- پس از استعلام ناموفق، هم فروشگاه‌های دیگر دارای همان محصول و هم محصولات جانشین هم‌دسته جست‌وجو می‌شوند. تمام شروط hard بر هر دو گروه اعمال می‌شوند. شناسه محصول جانشین به candidateهای مأموریت اضافه می‌شود تا امکان استعلام بعدی وجود داشته باشد.
- شرط hard خرید اعتباری که از متن صریح کاربر تشخیص داده شده، با مقدار `false` مدل تضعیف نمی‌شود. بودجه‌ای که صریحاً در متن فعلی آمده بر مقدار قبلی جایگزین می‌شود و بعد از پردازش گراف در مأموریت persist می‌شود.
- تنظیمات اختیاری: `LLM_ENABLED`, `LLM_PROVIDER=openai|openai_compatible`, `LLM_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL`, `LLM_TIMEOUT_SECONDS`. این متغیرها فقط در محیط backend تنظیم شوند. بدون کلید و مدل، هیچ درخواست بیرونی ارسال نمی‌شود.
- UI از قرارداد `ui.component` با registry محدود سمت React استفاده می‌کند؛ `component_stack` می‌تواند چند قطعه هم‌زمان را کنار هم بچیند. payloadهای پشتیبانی‌شده در بخش ۸ این سند آمده‌اند؛ داده‌ها از سرور اعتبارسنجی‌شده می‌آیند و UI دلخواه مدل اجرا نمی‌شود.
- تماس‌ها کاملاً شبیه‌سازی‌شده‌اند. هیچ شماره‌ای از این endpoint تماس واقعی دریافت نمی‌کند و outcome در کلاینت قابل‌انتخاب نیست.

## 13. قرارداد اجرایی Generative UI

رابط از HTML یا JavaScript تولیدشده توسط مدل استفاده نمی‌کند. عامل برای هر وضعیت خرید، یک `ui.component` با `component` و `data` می‌فرستد. اگر لازم باشد چند بخش هم‌زمان نمایش داده شوند، نوع `component_stack` استفاده می‌شود و `data.components` فهرستی از اجزای ثبت‌شده است. فرانت‌اند فقط نوع‌های مجاز را به کامپوننت React نگاشت می‌کند؛ نوع ناشناخته به fallback امن می‌رود.

### کامپوننت‌های فعلی و قرارداد داده

- `clarification_form`: وقتی عبارت محصول پس از حذف عبارت‌های عمومی خالی است؛ فرم محصول، سقف بودجه، شرط خرید اعتباری حضوری و ترتیب نمایش را نشان می‌دهد.
- `product_results`: فهرست محصولات و آفرهای واجد شرایط؛ داده محصول و قیمت از جست‌وجوی دیتابیس می‌آید.
- `category_choice`: وقتی سرویس کاتالوگ یک عبارت عمومی را به دامنه پیش‌فرض محدود می‌کند، گزینه تغییر دامنه را با `alternative_query` نمایش می‌دهد؛ برای نمونه پزشکی به صنعتی.
- `empty_state`: نتیجه بدون گزینه منطبق؛ فرم اصلاح عبارت و شروط سخت را نشان می‌دهد و هیچ شرطی خودکار حذف نمی‌شود.
- `comparison_table`: جدول مقایسه‌ای که `columns` و `rows` ساختاریافته دارد.
- `contact_progress` / `contact_status`: وضعیت استعلام. نتیجه تماس فقط از API شبیه‌ساز سرور پذیرفته می‌شود.
- `visit_plan`: فقط بعد از تأیید شبیه‌سازی‌شده، اطلاعات محصول، فروشگاه، قیمت ثبت‌شده، زمان تغییر قیمت و نشانی را در یک برنامه مراجعه جمع می‌کند.
- `notice`: توضیح کوتاه و غیرتعاملی برای وضعیت‌های کمکی.

فرم از فهرست کنترل‌شده فیلدها استفاده می‌کند: `text`، `number`، `checkbox` و `select`/`radio`. برای هر submit، فقط مقادیر ساختاریافته به handler ارسال می‌شود. handler سمت کلاینت عملیات را به اکشن‌های ازپیش‌تعریف‌شده مانند جست‌وجو، انتخاب دامنه یا اعمال فیلتر نگاشت می‌کند؛ `action` دلخواه یا کد اجرایی از سرور اجرا نمی‌شود.

### رفتار حالت‌ها

| وضعیت مأموریت | رابط ترجیحی |
|---|---|
| درخواست فاقد نام محصول | فرم تکمیل درخواست |
| نتایج معتبر | کارت‌های محصول با مقایسه آفرها |
| واژه عمومی و دارای پیشنهاد دامنه | انتخاب یک‌لمسی دامنه + نتایج |
| نتیجه خالی | فرم ویرایش عبارت/بودجه/خرید اعتباری |
| استعلام بی‌پاسخ/ناموجود/بسته/خطا | نتیجه وضعیت + گزینه‌های جایگزین موجود |
| تأیید موجودی در سناریوی دمو | برنامه مراجعه با منبع شبیه‌سازی مشخص |

قیمت ثبت‌شده از موجودی جاری جدا می‌ماند؛ برنامه مراجعه نیز صریحاً اعلام می‌کند تأیید موجودی از سناریوی دمو است و هیچ تماس واقعی انجام نشده است. اگر بودجه در فرم پاک شود، `max_price_toman: null` عمداً ارسال می‌شود تا backend آن را از شروط قبلی پاک کند؛ حذف کلید به‌تنهایی برای این کار کافی نیست.
