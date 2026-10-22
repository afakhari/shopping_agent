import { useEffect, useRef, useState, type FormEvent } from 'react'
import { AlertCircle, ArrowLeft, CheckCircle2, ChevronDown, ChevronUp, Clock3, CreditCard, ExternalLink, Headphones, HeartPulse, Laptop, LoaderCircle, LocateFixed, MapPin, MapPinOff, PhoneCall, Send, ShieldCheck, SlidersHorizontal, Sparkles, Store, RotateCcw } from 'lucide-react'
import { getProductOffers, type CatalogOffer, type CatalogSearchResult, type ProductOffersResponse } from '../search/catalog-api'
import { buildComparisonSpecColumns } from './comparison-specs'
import { isGreetingOnly } from './greeting-intent'
import { GenUIRenderer } from './GenUIRenderer'
import { formatDistance, formatLastPriceChange, getPriceQualityLabel, openStreetMapUrl } from './ui-formatters'
import { getResultPayload, getUIComponents, type GenUIAction, type GenUIComponent } from './genui-types'
import {
  createContactAttempt,
  createMission,
  getMission,
  isProductResultPayload,
  sendMissionTurn,
  type ContactAttemptResponse,
  type ContactAttemptRecord,
  type MissionConstraints,
  type MissionEvent,
} from './mission-api'

const money = new Intl.NumberFormat('fa-IR', { maximumFractionDigits: 0 })
const OUTCOME_LABELS: Record<ContactAttemptResponse['attempt']['outcome'], string> = {
  confirmed_available: 'موجودی در سناریوی دمو تأیید شد',
  unavailable: 'کالا در سناریوی دمو ناموجود است',
  no_answer: 'فروشگاه در سناریوی دمو پاسخ نداد',
  closed: 'فروشگاه در سناریوی دمو بسته است',
  error: 'استعلام در سناریوی دمو ناموفق بود',
  price_changed: 'تغییر قیمت در سناریوی دمو گزارش شد؛ مبلغ جدید مشخص نیست',
}

function formatPrice(price: string | null): string {
  if (!price) return 'قیمت ثبت نشده'
  try { return `${money.format(BigInt(price))} تومان` } catch { return 'قیمت نامشخص' }
}

function formatPersianDateTime(value: string | null): string | null {
  if (!value) return null
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return null
  return new Intl.DateTimeFormat('fa-IR', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: 'Asia/Tehran',
  }).format(date)
}

function ProductThumbnail({ src, title }: { src: string | undefined; title: string }) {
  const [failed, setFailed] = useState(false)
  if (!src || failed) {
    return (
      <span className="mission-product-image-fallback" role="img" aria-label={`تصویر محصول ${title} در دسترس نیست`}>
        <Store size={23} aria-hidden="true" />
        <small>تصویر موجود نیست</small>
      </span>
    )
  }
  return <img src={src} alt={title} loading="lazy" decoding="async" onError={() => setFailed(true)} />
}

function normalizeDigits(value: string): string {
  return value
    .replace(/[۰-۹]/g, (digit) => String('۰۱۲۳۴۵۶۷۸۹'.indexOf(digit)))
    .replace(/[٠-٩]/g, (digit) => String('٠١٢٣٤٥٦٧٨٩'.indexOf(digit)))
}

function readText(payload: Record<string, unknown>, key: string): string | null {
  const value = payload[key]
  return typeof value === 'string' ? value : null
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

const ACTIVE_MISSION_KEY = 'bazaar-compass:active-mission'
// The imported store dataset covers Tehran. Prevent a browser location elsewhere from creating
// a misleading zero-result "near me" search over Tehran-only shops. These are broad city bounds.
function isWithinTehranDataset(lat: number, lon: number): boolean {
  return lat >= 35.35 && lat <= 35.95 && lon >= 50.9 && lon <= 51.85
}

function readStoredMissionId(): string | null {
  try {
    return sessionStorage.getItem(ACTIVE_MISSION_KEY)
  } catch {
    return null
  }
}

function storeMissionId(missionId: string | null): void {
  try {
    if (missionId) sessionStorage.setItem(ACTIVE_MISSION_KEY, missionId)
    else sessionStorage.removeItem(ACTIVE_MISSION_KEY)
  } catch {
    // Persistence is progressive enhancement; mission APIs still work without storage.
  }
}

function restoreContactResponses(events: MissionEvent[]): Record<string, ContactAttemptResponse> {
  const restored: Record<string, ContactAttemptResponse> = {}
  let latestOfferId: string | null = null

  for (const event of events) {
    if (event.type === 'contact.completed' && isRecord(event.payload.attempt)) {
      const rawAttempt = event.payload.attempt
      if (typeof rawAttempt.offer_id !== 'string' || typeof rawAttempt.outcome !== 'string') continue
      const attempt = rawAttempt as unknown as ContactAttemptRecord
      latestOfferId = attempt.offer_id
      restored[latestOfferId] = { attempt, alternatives: [], alternative_products: [], events: [event] }
      continue
    }

    if (
      event.type === 'ui.component' &&
      readText(event.payload, 'component') === 'alternative_options' &&
      latestOfferId &&
      isRecord(event.payload.data)
    ) {
      const data = event.payload.data
      const previous = restored[latestOfferId]
      if (!previous) continue
      restored[latestOfferId] = {
        ...previous,
        alternatives: Array.isArray(data.alternatives) ? data.alternatives as CatalogOffer[] : [],
        alternative_products: Array.isArray(data.alternative_products)
          ? data.alternative_products as CatalogSearchResult[]
          : [],
      }
    }
  }
  return restored
}

function describeMissionEvent(event: MissionEvent): { title: string; detail?: string } | null {
  if (event.type === 'stage') {
    const label = readText(event.payload, 'label')
    return { title: label || 'بررسی اطلاعات خرید' }
  }
  if (event.type === 'contact.completed') {
    const attempt = isRecord(event.payload.attempt) ? event.payload.attempt : event.payload
    const outcome = readText(attempt, 'outcome')
    const shopName = readText(attempt, 'shop_name')
    const outcomeLabel = outcome && Object.prototype.hasOwnProperty.call(OUTCOME_LABELS, outcome)
      ? OUTCOME_LABELS[outcome as ContactAttemptResponse['attempt']['outcome']]
      : 'نتیجه استعلام ثبت شد'
    return { title: outcomeLabel, ...(shopName ? { detail: shopName } : {}) }
  }
  if (event.type === 'turn.completed') {
    const total = event.payload.total
    const status = readText(event.payload, 'status')
    const title = status === 'failed'
      ? 'بررسی کامل نشد'
      : status === 'waiting_for_user'
        ? 'منتظر انتخاب تو'
        : 'بررسی درخواست کامل شد'
    const detail = typeof total === 'number' && Number.isFinite(total)
      ? `${money.format(total)} محصول با شروط جاری بررسی شد`
      : undefined
    return { title, ...(detail ? { detail } : {}) }
  }
  return null
}

function formatBudgetLabel(value: string): string | null {
  const digits = normalizeDigits(value).replace(/[^0-9]/g, '')
  if (!digits) return null
  try { return `${money.format(BigInt(digits))} تومان` } catch { return null }
}

type ProductOfferView = {
  offers: CatalogOffer[]
  total: number
  page: number
  pageSize: number
  loading: boolean
  error: string | null
  expanded: boolean
}

function ProductResults({
  results,
  missionId,
  onContact,
  contactingOfferId,
  contactByOffer,
  selectedCompareProductIds,
  onToggleCompare,
  offerViews,
  onToggleOffers,
  onLoadMoreOffers,
  allowActions = true,
}: {
  results: CatalogSearchResult[]
  missionId: string
  onContact: (result: CatalogSearchResult) => void
  contactingOfferId: string | null
  contactByOffer: Record<string, ContactAttemptResponse>
  selectedCompareProductIds: string[]
  onToggleCompare: (result: CatalogSearchResult) => void
  offerViews: Record<string, ProductOfferView>
  onToggleOffers: (result: CatalogSearchResult) => void
  onLoadMoreOffers: (result: CatalogSearchResult) => void
  allowActions?: boolean
}) {
  const [showAllResults, setShowAllResults] = useState(false)
  if (results.length === 0) return <p className="mission-empty-results">با این عبارت و شرایط، محصول واجد شرایطی پیدا نشد. می‌توانی عبارت یا شروط خرید را تغییر بدهی.</p>
  const visibleResults = showAllResults ? results : results.slice(0, 4)
  return (
    <div className="mission-product-results" aria-label="نتایج محصولات">
      {visibleResults.map((result) => {
        const offer = result.best_offer
        const contact = contactByOffer[offer.id]
        const offerView = offerViews[result.product.id]
        const offersPanelId = `seller-offers-${result.product.id.replace(/[^a-zA-Z0-9_-]/g, '-')}`
        const imageUrl = result.product.images.find((value) => /^https?:\/\//i.test(value))
        const address = offer.shop.address ?? offer.shop.location_label ?? 'نشانی ثبت نشده'
        const priceUpdatedAt = formatPersianDateTime(offer.last_price_changed_at)
        const priceUpdatedRelative = formatLastPriceChange(offer.last_price_changed_at)
        const distanceLabel = formatDistance(offer.shop.distance_m)
        const mapUrl = openStreetMapUrl(offer.shop.lat, offer.shop.lon)
        const isCompared = selectedCompareProductIds.includes(result.product.id)
        return (
          <article className={`mission-product-card ${isCompared ? 'is-compared' : ''} ${allowActions && offerView?.expanded ? 'is-offers-expanded' : ''}`} key={result.product.id}>
            <div className="mission-product-image">
              <ProductThumbnail src={imageUrl} title={result.product.title} />
            </div>
            <div className="mission-product-main">
              <div className="mission-product-heading-row">
                <strong title={result.product.title}>{result.product.title}</strong>
                {isCompared && <span className="mission-compared-badge"><CheckCircle2 size={13} /> انتخاب‌شده</span>}
              </div>
              <div className="mission-product-price-line">
                <strong className="mission-product-price">{formatPrice(offer.price_toman)}</strong>
                <span className="mission-product-seller"><Store size={13} aria-hidden="true" />{offer.shop.name}</span>
              </div>
              <div className="mission-product-meta">
                <span className={`mission-price-quality ${offer.price_quality}`}><i />{getPriceQualityLabel(offer.price_quality)}</span>
                <span className="mission-offer-count"><Store size={13} />{money.format(result.eligible_offers_count)} فروشگاه</span>
                {offer.shop.accepts_in_person_credit && (
                  <span className="mission-credit-confirmed"><CreditCard size={12} /> اعتباری</span>
                )}
              </div>
              <details className="mission-product-details">
                <summary>
                  جزئیات
                  <ChevronDown size={14} aria-hidden="true" />
                </summary>
                <div className="mission-product-details-content">
                  <small className="mission-product-updated" title={priceUpdatedAt ? `زمان دقیق ثبت‌شده: ${priceUpdatedAt}` : undefined}>
                    <Clock3 size={13} aria-hidden="true" />{priceUpdatedRelative}
                    {priceUpdatedAt && <span className="mission-product-updated-exact">({priceUpdatedAt})</span>}
                  </small>
                  <small className="mission-product-address"><MapPin size={13} aria-hidden="true" />{address}</small>
                  {distanceLabel && <small className="mission-product-distance"><LocateFixed size={13} aria-hidden="true" />فاصلهٔ مستقیم: {distanceLabel}</small>}
                  {mapUrl && <a className="mission-map-link" href={mapUrl} target="_blank" rel="noopener noreferrer">
                    <MapPin size={13} aria-hidden="true" /> نمایش موقعیت ثبت‌شده روی نقشه <ExternalLink size={12} aria-hidden="true" />
                  </a>}
                  {!offer.shop.accepts_in_person_credit && (
                    <span className="mission-credit-unknown"><CreditCard size={13} aria-hidden="true" /> اطلاعات خرید اعتباری حضوری ثبت نشده</span>
                  )}
                  {result.reasons.length > 0 && (
                    <div className="mission-product-reasons" aria-label="دلایل نمایش این پیشنهاد">
                      {result.reasons.slice(0, 3).map((reason) => <span key={reason}><CheckCircle2 size={12} />{reason}</span>)}
                    </div>
                  )}
                  <small className="mission-product-disclaimer">قیمت و موجودی حضوری نیاز به استعلام فروشنده دارند.</small>
                </div>
              </details>
              <div className="mission-product-actions">
                {allowActions ? (
                  <button
                    type="button"
                    className="mission-offers-toggle"
                    aria-expanded={Boolean(offerView?.expanded)}
                    aria-controls={offersPanelId}
                    onClick={() => onToggleOffers(result)}
                    disabled={Boolean(offerView?.loading && !offerView.expanded)}
                  >
                    {offerView?.loading && !offerView.offers.length ? <LoaderCircle size={16} className="spin" /> : <Store size={16} />}
                    {offerView?.expanded ? 'بستن فروشگاه‌ها' : 'دیدن فروشگاه‌ها'}
                    <ArrowLeft size={14} className={offerView?.expanded ? 'offer-chevron open' : 'offer-chevron'} />
                  </button>
                ) : (
                  <span className="mission-price-note">برای بررسی دوباره، این جست‌وجو را از گفتگوی جاری اجرا کن.</span>
                )}
                {allowActions && (
                  <button
                    type="button"
                    className={`mission-compare-button ${isCompared ? 'selected' : ''}`}
                    aria-pressed={isCompared}
                    aria-label={`${isCompared ? 'حذف' : 'افزودن'} ${result.product.title} ${isCompared ? 'از' : 'به'} مقایسه`}
                    onClick={() => onToggleCompare(result)}
                  >
                    {isCompared ? <CheckCircle2 size={15} /> : <SlidersHorizontal size={15} />}
                    {isCompared ? 'انتخاب‌شده' : 'مقایسه'}
                  </button>
                )}
              </div>
              {allowActions && offerView?.expanded && (
                <section id={offersPanelId} className="mission-offer-list" aria-label={`فروشگاه‌های ${result.product.title}`} aria-busy={offerView.loading}>
                  <div className="mission-offer-list-heading">
                    <div><strong>فروشگاه‌ها و قیمت‌ها</strong><span>قیمت‌های ثبت‌شده برای همین مدل</span></div>
                    <span className="mission-offer-total">{money.format(offerView.total || result.eligible_offers_count)} مورد</span>
                  </div>
                  {offerView.loading && offerView.offers.length === 0 && <div className="mission-offer-state"><LoaderCircle size={17} className="spin" /> در حال دریافت فروشگاه‌های واجد شرایط…</div>}
                  {offerView.error && <div className="mission-offer-error" role="alert"><span>{offerView.error}</span><button type="button" onClick={() => onToggleOffers(result)}>تلاش دوباره</button></div>}
                  {!offerView.loading && !offerView.error && offerView.offers.length === 0 && <p className="mission-offer-state">فروشگاهی با این شروط برای این مدل پیدا نشد.</p>}
                  {offerView.offers.map((sellerOffer) => {
                    const attempt = contactByOffer[sellerOffer.id]
                    const sellerDistance = formatDistance(sellerOffer.shop.distance_m)
                    const sellerUpdatedAt = formatPersianDateTime(sellerOffer.last_price_changed_at)
                    const sellerMapUrl = openStreetMapUrl(sellerOffer.shop.lat, sellerOffer.shop.lon)
                    return (
                      <article className="mission-offer-row" key={sellerOffer.id}>
                        <div className="mission-offer-copy">
                          <strong>{sellerOffer.shop.name}</strong>
                          <span className="mission-offer-price">{formatPrice(sellerOffer.price_toman)}</span>
                          <small><MapPin size={12} />{sellerOffer.shop.address ?? sellerOffer.shop.location_label ?? 'نشانی ثبت نشده'}</small>
                          {sellerDistance && <small><LocateFixed size={12} />فاصله مستقیم: {sellerDistance}</small>}
                          {sellerMapUrl && <a className="mission-offer-map" href={sellerMapUrl} target="_blank" rel="noopener noreferrer"><MapPin size={12} /> نمایش روی نقشه <ExternalLink size={11} /></a>}
                          <div className="mission-offer-badges">
                            <span className={`mission-price-quality ${sellerOffer.price_quality}`}><i />{getPriceQualityLabel(sellerOffer.price_quality)}</span>
                            <span className={`mission-shop-credit ${sellerOffer.shop.accepts_in_person_credit ? 'registered' : 'unknown'}`}><CreditCard size={12} />{sellerOffer.shop.accepts_in_person_credit ? 'اعتبار حضوری ثبت شده' : 'اطلاعات اعتبار ثبت نشده'}</span>
                          </div>
                          {sellerUpdatedAt && <small className="mission-offer-updated"><Clock3 size={12} />آخرین تغییر: {sellerUpdatedAt}</small>}
                        </div>
                        <button
                          type="button"
                          className="mission-offer-verify"
                          onClick={() => onContact({ ...result, best_offer: sellerOffer })}
                          disabled={contactingOfferId === sellerOffer.id || !missionId}
                        >
                          {contactingOfferId === sellerOffer.id ? <LoaderCircle size={15} className="spin" /> : <ShieldCheck size={15} />}
                          {contactingOfferId === sellerOffer.id ? 'در حال بررسی…' : 'بررسی پیش از مراجعه'}
                        </button>
                        {attempt && sellerOffer.id !== offer.id && <div className={`mission-offer-attempt ${attempt.attempt.outcome === 'confirmed_available' ? 'success' : 'warning'}`} aria-live="polite"><strong>{OUTCOME_LABELS[attempt.attempt.outcome]}</strong><span>{attempt.attempt.response_text}</span></div>}
                      </article>
                    )
                  })}
                  {offerView.offers.length < offerView.total && (
                    <button type="button" className="mission-offer-load-more" onClick={() => onLoadMoreOffers(result)} disabled={offerView.loading}>
                      {offerView.loading ? <LoaderCircle size={15} className="spin" /> : null}
                      {offerView.loading ? 'در حال دریافت…' : `نمایش فروشگاه‌های بیشتر (${money.format(offerView.offers.length)} از ${money.format(offerView.total)})`}
                    </button>
                  )}
                </section>
              )}
              {contact && (
                <div className={`mission-contact-result ${contact.attempt.outcome === 'confirmed_available' ? 'success' : 'warning'}`} aria-live="polite">
                  <strong>{OUTCOME_LABELS[contact.attempt.outcome]}</strong>
                  <span>{contact.attempt.response_text}</span>
                  {contact.alternatives.length > 0 && (
                    <div className="mission-alternatives">
                      <b>گزینه‌های جایگزین</b>
                      {contact.alternatives.slice(0, 3).map((alternative: CatalogOffer) => (
                        <div key={alternative.id}><span>{alternative.shop.name}</span><strong>{formatPrice(alternative.price_toman)}</strong></div>
                      ))}
                    </div>
                  )}
                  {contact.alternative_products?.length > 0 && (
                    <div className="mission-alternative-products">
                      <b>مدل‌های جایگزین با شروط مشابه</b>
                      {contact.alternative_products.slice(0, 3).map((alternative) => {
                        const alternativeOffer = alternative.best_offer
                        const alternativeAttempt = contactByOffer[alternativeOffer.id]
                        const alternativeImage = alternative.product.images.find((value) => /^https?:\/\//i.test(value))
                        return (
                          <div className="mission-alternative-product" key={alternative.product.id}>
                            <div className="mission-alternative-thumb">
                              {alternativeImage
                                ? <img src={alternativeImage} alt="" loading="lazy" />
                                : <Store size={17} />}
                            </div>
                            <div className="mission-alternative-copy">
                              <strong>{alternative.product.title}</strong>
                              <span>{alternativeOffer.shop.name} · {formatPrice(alternativeOffer.price_toman)}</span>
                              {alternativeAttempt && <small>{OUTCOME_LABELS[alternativeAttempt.attempt.outcome]}</small>}
                            </div>
                            <button
                              type="button"
                              className="mission-alternative-action"
                              onClick={() => onContact(alternative)}
                              disabled={contactingOfferId === alternativeOffer.id || !missionId}
                            >
                              {contactingOfferId === alternativeOffer.id
                                ? <LoaderCircle size={14} className="spin" />
                                : <PhoneCall size={14} />}
                              بررسی
                            </button>
                          </div>
                        )
                      })}
                    </div>
                  )}
                </div>
              )}
            </div>
          </article>
        )
      })}
      {results.length > 4 && (
        <button type="button" className="mission-more-results" onClick={() => setShowAllResults((visible) => !visible)} aria-expanded={showAllResults}>
          {showAllResults ? <>نمایش گزینه‌های کمتر <ChevronUp size={16} /></> : <>نمایش {new Intl.NumberFormat('fa-IR').format(results.length - visibleResults.length)} گزینهٔ دیگر <ChevronDown size={16} /></>}
        </button>
      )}
    </div>
  )
}

type MissionChatMessage = {
  id: string
  role: 'user' | 'assistant'
  text: string
  components: GenUIComponent[]
  /** undefined means this message did not return a catalog result surface. */
  results?: CatalogSearchResult[]
  resultCount?: number
  query?: string
  pending?: boolean
}

const PRIMARY_SEARCH_COMPONENTS = new Set([
  'product_results', 'empty_state', 'clarification_form', 'category_choice',
  'filter_form', 'constraint_form',
])
const PRE_RESULT_COMPONENTS = new Set([
  'category_choice', 'empty_state', 'clarification_form', 'filter_form', 'constraint_form', 'notice',
])

function findLastPendingAssistantIndex(messages: MissionChatMessage[]): number {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const message = messages[index]
    if (message?.role === 'assistant' && message.pending) return index
  }
  return -1
}

function mergeUIEventIntoMessages(messages: MissionChatMessage[], event: MissionEvent): MissionChatMessage[] {
  const incoming = getUIComponents(event)
  if (!incoming.length) return messages

  const next = [...messages]
  let assistantIndex = -1
  for (let index = next.length - 1; index >= 0; index -= 1) {
    if (next[index]?.role === 'assistant') {
      assistantIndex = index
      break
    }
  }
  if (assistantIndex < 0) {
    next.push({ id: `assistant-ui-${event.seq}`, role: 'assistant', text: 'اطلاعات تکمیلی مأموریت', components: [] })
    assistantIndex = next.length - 1
  }

  const existing = next[assistantIndex]
  if (!existing) return messages
  const primarySurface = incoming.some((component) => PRIMARY_SEARCH_COMPONENTS.has(component.type))
  const productPayload = getResultPayload(incoming)
  let components: GenUIComponent[]
  if (primarySurface) {
    components = incoming.filter((component) => component.type !== 'product_results')
  } else {
    components = [
      ...existing.components.filter((saved) => !incoming.some((item) => item.type === saved.type)),
      ...incoming,
    ]
  }

  const updated: MissionChatMessage = { ...existing, components }
  if (isProductResultPayload(productPayload)) {
    updated.results = productPayload.results
    updated.resultCount = productPayload.total
    if (typeof productPayload.query === 'string') updated.query = productPayload.query
  } else if (incoming.some((component) => ['empty_state', 'clarification_form'].includes(component.type))) {
    updated.results = []
    updated.resultCount = 0
    const queryComponent = incoming.find((component) => ['empty_state', 'clarification_form'].includes(component.type))
    if (queryComponent && typeof queryComponent.data.query === 'string') updated.query = queryComponent.data.query
  } else if (primarySurface) {
    delete updated.results
    delete updated.resultCount
  }
  next[assistantIndex] = updated
  return next
}

function rebuildChatFromEvents(events: MissionEvent[]): MissionChatMessage[] {
  const messages: MissionChatMessage[] = []
  let awaitingAssistant = false
  for (const event of [...events].sort((left, right) => left.seq - right.seq)) {
    if (event.type === 'user.message') {
      const value = readText(event.payload, 'message')
      if (value) messages.push({ id: `user-${event.seq}`, role: 'user', text: value, components: [] })
      awaitingAssistant = true
      continue
    }
    if (event.type === 'assistant.message') {
      const value = readText(event.payload, 'text')
      if (value) messages.push({ id: `assistant-${event.seq}`, role: 'assistant', text: value, components: [] })
      awaitingAssistant = false
      continue
    }
    if (event.type === 'ui.component') {
      // During a normal turn the assistant.message event precedes this event. Older snapshots
      // may lack that event, so create a safe, explicit fallback message rather than losing UI.
      if (awaitingAssistant) {
        messages.push({ id: `assistant-fallback-${event.seq}`, role: 'assistant', text: 'نتیجهٔ این مرحله آماده است.', components: [] })
        awaitingAssistant = false
      }
      const merged = mergeUIEventIntoMessages(messages, event)
      messages.splice(0, messages.length, ...merged)
    }
  }
  return messages
}

function appendLocalComponent(messages: MissionChatMessage[], component: GenUIComponent): MissionChatMessage[] {
  const next = [...messages]
  let index = -1
  for (let cursor = next.length - 1; cursor >= 0; cursor -= 1) {
    if (next[cursor]?.role === 'assistant') {
      index = cursor
      break
    }
  }
  if (index < 0) {
    next.push({ id: `assistant-local-${Date.now()}`, role: 'assistant', text: 'می‌توانیم شرایط جست‌وجو را دقیق‌تر کنیم.', components: [component] })
    return next
  }
  const current = next[index]
  if (!current) return messages
  next[index] = {
    ...current,
    components: [...current.components.filter((saved) => saved.type !== component.type), component],
  }
  return next
}

export function MissionPanel({
  budget,
  mustHaveCredit,
  location,
  radiusM,
  sort,
  onLocationChange,
  onRestoreConstraints,
}: {
  budget: string
  mustHaveCredit: boolean
  location: { lat: number; lon: number } | null
  radiusM: number
  sort: NonNullable<MissionConstraints['sort']>
  onLocationChange: (location: { lat: number; lon: number } | null) => void
  onRestoreConstraints: (constraints: MissionConstraints, restoredMessage: string) => void
}) {
  const [initialMissionId] = useState<string | null>(readStoredMissionId)
  const [message, setMessage] = useState('')
  const [missionId, setMissionId] = useState<string | null>(initialMissionId)
  const [isRestoring, setIsRestoring] = useState(Boolean(initialMissionId))
  const [events, setEvents] = useState<MissionEvent[]>([])
  const [chatMessages, setChatMessages] = useState<MissionChatMessage[]>([])
  const [lastQuery, setLastQuery] = useState('')
  const [selectedCompareProductIds, setSelectedCompareProductIds] = useState<string[]>([])
  const [isRunning, setIsRunning] = useState(false)
  const [contactingOfferId, setContactingOfferId] = useState<string | null>(null)
  const [contactByOffer, setContactByOffer] = useState<Record<string, ContactAttemptResponse>>({})
  const [offerViews, setOfferViews] = useState<Record<string, ProductOfferView>>({})
  const offerRequestControllers = useRef(new Map<string, AbortController>())
  const [error, setError] = useState<string | null>(null)
  const [stageLabel, setStageLabel] = useState<string | null>(null)
  const [isLocating, setIsLocating] = useState(false)
  const transcriptEndRef = useRef<HTMLDivElement | null>(null)
  const composerInputRef = useRef<HTMLTextAreaElement | null>(null)
  const turnCounter = useRef(0)

  const constraints: MissionConstraints = {
    city: 'tehran',
    ...(budget.trim() ? { max_price_toman: budget.trim() } : {}),
    must_have_in_person_credit: mustHaveCredit,
    sort: location || sort !== 'distance_asc' ? sort : 'relevance',
    ...(location ? { lat: location.lat, lon: location.lon, radius_m: radiusM } : {}),
  }

  const currentAssistantMessage = [...chatMessages].reverse().find((item) => item.role === 'assistant')
  const results = currentAssistantMessage?.results ?? []

  useEffect(() => {
    const restoreId = initialMissionId
    if (!restoreId) return

    const controller = new AbortController()
    void getMission(restoreId, controller.signal)
      .then((snapshot) => {
        const history = snapshot.events ?? []
        setEvents(history)
        setContactByOffer(restoreContactResponses(history))
        const restoredMessages = rebuildChatFromEvents(history)
        setChatMessages(restoredMessages)
        let restoredProductQuery: string | null = null
        for (const item of [...restoredMessages].reverse()) {
          const resultComponent = item.components.find((component) => component.type === 'empty_state')
          if (item.results !== undefined) {
            if (item.query) restoredProductQuery = item.query
            break
          }
          if (resultComponent && typeof resultComponent.data.query === 'string') {
            restoredProductQuery = resultComponent.data.query
            break
          }
        }
        const latestStage = [...history].reverse().find((event) => event.type === 'stage' || event.type === 'assistant.message')
        setStageLabel(latestStage
          ? readText(latestStage.payload, latestStage.type === 'stage' ? 'label' : 'text')
          : 'مأموریت قبلی بازیابی شد؛ می‌توانی آن را ادامه بدهی.')
        const restoredMessage = typeof snapshot.state?.last_turn_message === 'string'
          ? snapshot.state.last_turn_message
          : snapshot.initial_message
        setLastQuery(restoredProductQuery ?? restoredMessage)
        onRestoreConstraints(snapshot.constraints, restoredMessage)
      })
      .catch((reason: unknown) => {
        if (controller.signal.aborted) return
        storeMissionId(null)
        setMissionId(null)
        setError(reason instanceof Error
          ? `بازیابی مأموریت قبلی ممکن نشد: ${reason.message} می‌توانی مأموریت تازه‌ای شروع کنی.`
          : 'بازیابی مأموریت قبلی ممکن نشد؛ یک مأموریت تازه شروع کن.')
      })
      .finally(() => {
        if (!controller.signal.aborted) setIsRestoring(false)
      })

    return () => controller.abort()
  }, [initialMissionId, onRestoreConstraints])

  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [chatMessages, isRunning])

  useEffect(() => {
    const input = composerInputRef.current
    if (!input) return
    input.style.height = 'auto'
    const maxHeight = 160
    input.style.height = `${Math.min(input.scrollHeight, maxHeight)}px`
    input.style.overflowY = input.scrollHeight > maxHeight ? 'auto' : 'hidden'
  }, [message])

  useEffect(() => () => {
    offerRequestControllers.current.forEach((controller) => controller.abort())
    offerRequestControllers.current.clear()
  }, [])

  const handleEvent = (event: MissionEvent) => {
    setEvents((current) => current.some((saved) => saved.seq === event.seq)
      ? current
      : [...current, event].sort((left, right) => left.seq - right.seq))

    if (event.type === 'stage') {
      const label = readText(event.payload, 'label')
      if (label) setStageLabel(label)
    }
    if (event.type === 'assistant.message') {
      const text = readText(event.payload, 'text')
      if (text) {
        setStageLabel(text)
        setChatMessages((current) => {
          const next = [...current]
          let pendingIndex = -1
          for (let index = next.length - 1; index >= 0; index -= 1) {
            if (next[index]?.role === 'assistant' && next[index]?.pending) {
              pendingIndex = index
              break
            }
          }
          if (pendingIndex >= 0 && next[pendingIndex]) {
            next[pendingIndex] = { ...next[pendingIndex]!, text, pending: false }
          } else {
            next.push({ id: `assistant-${event.seq}`, role: 'assistant', text, components: [] })
          }
          return next
        })
      }
    }
    if (event.type === 'ui.component') {
      const incoming = getUIComponents(event)
      setChatMessages((current) => mergeUIEventIntoMessages(current, event))
      if (incoming.some((component) => PRIMARY_SEARCH_COMPONENTS.has(component.type))) {
        setSelectedCompareProductIds([])
        offerRequestControllers.current.forEach((controller) => controller.abort())
        offerRequestControllers.current.clear()
        setOfferViews({})
      }
      const payload = getResultPayload(incoming)
      if (isProductResultPayload(payload) && typeof payload.query === 'string') {
        setLastQuery(payload.query)
      } else {
        const queryComponent = incoming.find((component) => ['empty_state', 'clarification_form'].includes(component.type))
        if (queryComponent && typeof queryComponent.data.query === 'string') setLastQuery(queryComponent.data.query)
      }
    }
  }

  const runTurn = async (turnMessage: string, turnConstraints: MissionConstraints = constraints, displayQuery = turnMessage) => {
    const trimmed = turnMessage.trim()
    if (!trimmed || isRunning || isRestoring) return
    // A salutation is not a catalog query. Avoid irrelevant product recommendations
    // and avoid creating a misleading purchase mission until a product intent exists.
    if (isGreetingOnly(trimmed)) {
      turnCounter.current += 1
      const greetingId = `hello-${Date.now()}-${turnCounter.current}`
      setChatMessages((current) => [
        ...current,
        { id: `user-${greetingId}`, role: 'user', text: trimmed, components: [] },
        {
          id: `assistant-${greetingId}`,
          role: 'assistant',
          text: 'سلام! خوش اومدی. 🌱 دنبال چه محصولی هستی؟ می‌تونی مدل، کاربرد یا حدود بودجه رو بگی تا گزینه‌های مناسب و فروشگاه‌های تهران رو بررسی کنیم.',
          components: [],
        },
      ])
      setMessage('')
      setError(null)
      return
    }
    setError(null)
    setIsRunning(true)
    setStageLabel('در حال آماده‌سازی مأموریت خرید...')
    setLastQuery(displayQuery.trim())
    turnCounter.current += 1
    const turnId = `${Date.now()}-${turnCounter.current}`
    setChatMessages((current) => [
      ...current,
      { id: `user-${turnId}`, role: 'user', text: trimmed, components: [] },
      { id: `assistant-${turnId}`, role: 'assistant', text: 'در حال تحلیل درخواست و بررسی آفرهای تهران…', components: [], pending: true },
    ])
    setMessage('')
    try {
      let activeMissionId = missionId
      if (!activeMissionId) {
        const created = await createMission(trimmed, turnConstraints)
        activeMissionId = created.mission_id
        setMissionId(activeMissionId)
        storeMissionId(activeMissionId)
      }
      await sendMissionTurn(activeMissionId, trimmed, turnConstraints, handleEvent)
    } catch (reason) {
      const errorText = reason instanceof Error ? reason.message : 'اجرای مأموریت ناموفق بود.'
      setError(errorText)
      setChatMessages((current) => {
        const next = [...current]
        const index = findLastPendingAssistantIndex(next)
        if (index >= 0 && next[index]) next[index] = { ...next[index]!, text: `نتوانستم این بررسی را کامل کنم: ${errorText}`, pending: false }
        return next
      })
    } finally {
      setIsRunning(false)
      setChatMessages((current) => {
        const next = [...current]
        const index = findLastPendingAssistantIndex(next)
        if (index >= 0 && next[index]) {
          next[index] = { ...next[index]!, text: 'درخواست ارسال شد، اما پاسخ کامل دریافت نشد. می‌توانی دوباره تلاش کنی.', pending: false }
        }
        return next
      })
    }
  }

  const handleLocationClick = () => {
    if (isLocating || isRunning || isRestoring) return
    if (location) {
      const nextConstraints: MissionConstraints = {
        city: 'tehran',
        ...(budget.trim() ? { max_price_toman: budget.trim() } : {}),
        must_have_in_person_credit: mustHaveCredit,
        sort: sort === 'distance_asc' ? 'relevance' : sort,
      }
      onLocationChange(null)
      onRestoreConstraints(nextConstraints, lastQuery)
      if (lastQuery.trim()) void runTurn(lastQuery, nextConstraints, lastQuery)
      else setChatMessages((current) => [...current, {
        id: `assistant-location-${Date.now()}`,
        role: 'assistant',
        text: 'موقعیت از این جست‌وجو حذف شد. برای محدودکردن نتایج به اطراف خودت، دوباره دکمهٔ موقعیت را بزن.',
        components: [],
      }])
      return
    }
    if (!navigator.geolocation) {
      setError('مرورگر این دستگاه موقعیت‌یابی را پشتیبانی نمی‌کند. می‌توانی بدون فیلتر فاصله جست‌وجو کنی.')
      return
    }
    setIsLocating(true)
    setError(null)
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const nextLocation = { lat: position.coords.latitude, lon: position.coords.longitude }
        if (!isWithinTehranDataset(nextLocation.lat, nextLocation.lon)) {
          setIsLocating(false)
          setError('دیتاست فروشگاه‌های این نسخه فقط تهران را پوشش می‌دهد و موقعیت فعلی بیرون از محدودهٔ آن است. فیلتر موقعیت اعمال نشد؛ می‌توانی جست‌وجوی تهران را بدون فاصله ادامه بدهی.')
          return
        }
        const nextConstraints: MissionConstraints = {
          city: 'tehran',
          ...(budget.trim() ? { max_price_toman: budget.trim() } : {}),
          must_have_in_person_credit: mustHaveCredit,
          lat: nextLocation.lat,
          lon: nextLocation.lon,
          radius_m: radiusM,
          sort: 'distance_asc',
        }
        onLocationChange(nextLocation)
        onRestoreConstraints(nextConstraints, lastQuery)
        setChatMessages((current) => [...current, {
          id: `assistant-location-${Date.now()}`,
          role: 'assistant',
          text: lastQuery.trim()
            ? 'موقعیت دستگاه با اجازهٔ خودت دریافت شد؛ جست‌وجو را با اولویت فروشگاه‌های نزدیک به‌روز می‌کنم.'
            : 'موقعیت با اجازهٔ خودت ثبت شد. از این پس می‌توانی فروشگاه‌ها را بر اساس فاصلهٔ مستقیم مرتب کنی. حالا محصول موردنظرت را بگو.',
          components: [],
        }])
        if (lastQuery.trim()) void runTurn(lastQuery, nextConstraints, lastQuery)
        setIsLocating(false)
      },
      (reason) => {
        setIsLocating(false)
        const text = reason.code === reason.PERMISSION_DENIED
          ? 'دسترسی به موقعیت رد شد. می‌توانی اجازهٔ موقعیت را در مرورگر فعال کنی یا بدون فیلتر فاصله ادامه بدهی.'
          : reason.code === reason.POSITION_UNAVAILABLE
            ? 'موقعیت فعلی در دسترس نیست. بدون فیلتر فاصله هم می‌توانی جست‌وجو کنی.'
            : 'دریافت موقعیت بیش از حد طول کشید. دوباره تلاش کن یا بدون فیلتر فاصله ادامه بده.'
        setError(text)
      },
      { enableHighAccuracy: false, timeout: 12000, maximumAge: 300000 },
    )
  }

  const toggleComparedProduct = (result: CatalogSearchResult) => {
    if (!selectedCompareProductIds.includes(result.product.id) && selectedCompareProductIds.length >= 3) {
      setError('برای مقایسه، حداکثر سه گزینه را انتخاب کن. ابتدا یکی را از مقایسه حذف کن.')
      return
    }
    setSelectedCompareProductIds((current) => current.includes(result.product.id)
      ? current.filter((id) => id !== result.product.id)
      : [...current, result.product.id])
  }

  const fetchProductOffers = async (result: CatalogSearchResult, page: number, append: boolean) => {
    const productId = result.product.id
    offerRequestControllers.current.get(productId)?.abort()
    const controller = new AbortController()
    offerRequestControllers.current.set(productId, controller)
    setOfferViews((current) => {
      const previous = current[productId]
      return {
        ...current,
        [productId]: {
          offers: previous?.offers ?? [],
          total: previous?.total ?? result.eligible_offers_count,
          page: previous?.page ?? 0,
          pageSize: previous?.pageSize ?? 8,
          loading: true,
          error: null,
          expanded: true,
        },
      }
    })
    try {
      const response: ProductOffersResponse = await getProductOffers(productId, {
        maxPriceToman: budget,
        mustHaveInPersonCredit: mustHaveCredit,
        location,
        radiusM: location ? radiusM : undefined,
        sort: constraints.sort ?? 'relevance',
        page,
        pageSize: 8,
      }, controller.signal)
      if (controller.signal.aborted) return
      setOfferViews((current) => {
        const previous = current[productId]
        const offers = append
          ? [...(previous?.offers ?? []), ...response.results.filter((newOffer) => !(previous?.offers ?? []).some((oldOffer) => oldOffer.id === newOffer.id))]
          : response.results
        return {
          ...current,
          [productId]: {
            offers,
            total: response.total,
            page: response.page,
            pageSize: response.page_size,
            loading: false,
            error: null,
            expanded: true,
          },
        }
      })
    } catch (reason) {
      if (controller.signal.aborted) return
      setOfferViews((current) => {
        const previous = current[productId]
        if (!previous) return current
        return {
          ...current,
          [productId]: {
            ...previous,
            loading: false,
            error: reason instanceof Error ? reason.message : 'دریافت فهرست فروشگاه‌ها ناموفق بود.',
            expanded: true,
          },
        }
      })
    } finally {
      if (offerRequestControllers.current.get(productId) === controller) {
        offerRequestControllers.current.delete(productId)
        setOfferViews((current) => {
          const previous = current[productId]
          return previous ? { ...current, [productId]: { ...previous, loading: false } } : current
        })
      }
    }
  }

  const toggleProductOffers = (result: CatalogSearchResult) => {
    const current = offerViews[result.product.id]
    if (current?.expanded && !current.error) {
      setOfferViews((views) => ({ ...views, [result.product.id]: { ...views[result.product.id]!, expanded: false } }))
      return
    }
    if (current?.offers.length && !current.error) {
      setOfferViews((views) => ({ ...views, [result.product.id]: { ...views[result.product.id]!, expanded: true } }))
      return
    }
    void fetchProductOffers(result, 1, false)
  }

  const loadMoreProductOffers = (result: CatalogSearchResult) => {
    const current = offerViews[result.product.id]
    if (!current || current.loading || current.offers.length >= current.total) return
    void fetchProductOffers(result, current.page + 1, true)
  }

  const handleGenUIAction = (action: GenUIAction) => {
    if (isRunning || isRestoring) return
    if (action.type === 'fill_query') {
      setMessage(action.query || lastQuery)
      composerInputRef.current?.focus()
      return
    }
    if (action.type === 'open_filter_form') {
      setChatMessages((current) => appendLocalComponent(current, {
        type: 'filter_form',
        id: `local-filter-form-${Date.now()}`,
        data: {
          title: 'شرایط خرید را تنظیم کن',
          description: 'هیچ شرطی بدون انتخاب تو تغییر نمی‌کند.',
          purpose: 'constraint_adjustment',
          submit_label: 'اعمال شرایط',
          fields: [
            { id: 'product_query', label: 'محصول', type: 'text', required: true, default_value: lastQuery },
            { id: 'max_price_toman', label: 'سقف بودجه (تومان)', type: 'number', required: false, min: 1, default_value: budget, helper_text: 'اختیاری؛ ارقام فارسی یا انگلیسی را وارد کن.' },
            { id: 'must_have_in_person_credit', label: 'فقط خرید اعتباری حضوری', type: 'checkbox', default_value: mustHaveCredit },
            ...(location ? [{ id: 'radius_m', label: 'حداکثر فاصلهٔ مستقیم', type: 'select' as const, required: true, default_value: String(radiusM), options: [
              { label: '۱ کیلومتر', value: '1000' },
              { label: '۳ کیلومتر', value: '3000' },
              { label: '۵ کیلومتر', value: '5000' },
              { label: '۱۰ کیلومتر', value: '10000' },
            ] }] : []),
            { id: 'sort', label: 'ترتیب نمایش', type: 'select', required: true, default_value: constraints.sort ?? 'relevance', options: [
              { label: 'مرتبط‌ترین', value: 'relevance' },
              { label: 'کمترین قیمت ثبت‌شده', value: 'price_asc' },
              ...(location ? [{ label: 'نزدیک‌ترین فروشگاه', value: 'distance_asc' }] : []),
              { label: 'تازه‌ترین تغییر قیمت', value: 'recent_price_change' },
            ] },
          ],
        },
      }))
      return
    }
    if (action.type === 'run_query') {
      onRestoreConstraints(constraints, action.query)
      void runTurn(action.query, constraints, action.query)
      return
    }
    if (action.type === 'submit_form') {
      const values = action.values
      const productValue = values.product_query ?? values.query
      const query = typeof productValue === 'string' && productValue.trim()
        ? productValue.trim()
        : lastQuery.trim()
      const hasBudgetField = Object.prototype.hasOwnProperty.call(values, 'max_price_toman') || Object.prototype.hasOwnProperty.call(values, 'budget')
      const rawBudget = values.max_price_toman ?? values.budget
      const normalizedBudget = rawBudget === undefined || rawBudget === null
        ? ''
        : normalizeDigits(String(rawBudget)).replace(/[^0-9]/g, '')
      const credit = Object.prototype.hasOwnProperty.call(values, 'must_have_in_person_credit')
        ? values.must_have_in_person_credit === true
        : mustHaveCredit
      const requestedSort = values.sort
      const allowedSort = requestedSort === 'price_asc' || requestedSort === 'recent_price_change'
          || (requestedSort === 'distance_asc' && Boolean(location))
        ? requestedSort as MissionConstraints['sort']
        : 'relevance'
      const rawRadius = values.radius_m
      const parsedRadius = Number(normalizeDigits(String(rawRadius ?? '')))
      const nextRadius = [1000, 3000, 5000, 10000].includes(parsedRadius) ? parsedRadius : radiusM
      const nextConstraints: MissionConstraints = {
        ...constraints,
        ...(hasBudgetField ? { max_price_toman: normalizedBudget || null } : {}),
        must_have_in_person_credit: credit,
        ...(location ? { lat: location.lat, lon: location.lon, radius_m: nextRadius } : {}),
        ...(Object.prototype.hasOwnProperty.call(values, 'sort') ? { sort: allowedSort } : {}),
      }
      if (!query) {
        setError('نام محصول را وارد کن تا بتوانم گزینه‌ها را پیدا کنم.')
        return
      }
      onRestoreConstraints(nextConstraints, query)
      void runTurn(query, nextConstraints, query)
    }
  }

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    await runTurn(message, constraints)
  }

  const contact = async (result: CatalogSearchResult) => {
    if (!missionId || contactingOfferId || isRunning) return
    const offer = result.best_offer
    setContactingOfferId(offer.id)
    setError(null)
    try {
      const response = await createContactAttempt(missionId, { shopId: offer.shop.id, offerId: offer.id })
      setContactByOffer((current) => ({ ...current, [offer.id]: response }))
      if (response.events?.length) {
        setEvents((current) => {
          const bySequence = new Map(current.map((event) => [event.seq, event]))
          response.events?.forEach((event) => bySequence.set(event.seq, event))
          return [...bySequence.values()].sort((left, right) => left.seq - right.seq)
        })
        setChatMessages((current) => response.events!.reduce((messages, event) =>
          event.type === 'ui.component' ? mergeUIEventIntoMessages(messages, event) : messages, current))
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'استعلام ناموفق بود.')
    } finally {
      setContactingOfferId(null)
    }
  }

  const startNewMission = () => {
    offerRequestControllers.current.forEach((controller) => controller.abort())
    offerRequestControllers.current.clear()
    setOfferViews({})
    setMissionId(null)
    storeMissionId(null)
    setMessage('')
    setEvents([])
    setChatMessages([])
    setLastQuery('')
    setSelectedCompareProductIds([])
    setContactByOffer({})
    setError(null)
    setStageLabel(null)
  }

  const selectedCompareResults = results.filter((result) => selectedCompareProductIds.includes(result.product.id))
  const specComparison = buildComparisonSpecColumns(selectedCompareResults.map((result) => result.product))
  const comparisonColumns = [
    { key: 'product', label: 'محصول' },
    { key: 'price', label: 'قیمت ثبت‌شده' },
    { key: 'shop', label: 'فروشگاه' },
    { key: 'address', label: 'نشانی' },
    { key: 'credit', label: 'خرید اعتباری حضوری' },
    { key: 'updated', label: 'آخرین تغییر قیمت' },
    { key: 'distance', label: 'فاصله مستقیم' },
    ...specComparison.columns,
  ]
  const comparisonRows = selectedCompareResults.map((result, index) => {
    const offer = result.best_offer
    let updated = 'زمان تغییر قیمت ثبت نشده'
    if (offer.last_price_changed_at) {
      const date = new Date(offer.last_price_changed_at)
      if (!Number.isNaN(date.getTime())) updated = new Intl.DateTimeFormat('fa-IR', { dateStyle: 'medium', timeZone: 'Asia/Tehran' }).format(date)
    }
    return {
      id: result.product.id,
      product: result.product.title,
      price: formatPrice(offer.price_toman),
      shop: offer.shop.name,
      address: offer.shop.address ?? offer.shop.location_label ?? 'نشانی ثبت نشده',
      credit: offer.shop.accepts_in_person_credit ? 'ثبت شده' : 'ثبت نشده',
      updated,
      distance: formatDistance(offer.shop.distance_m) ?? 'محاسبه نشده',
      ...specComparison.valuesByProduct[index],
    }
  })
  const comparisonComponents: GenUIComponent[] = selectedCompareResults.length >= 2
    ? [{
      type: 'comparison_table',
      id: 'live-selected-product-comparison',
      data: {
        title: 'مقایسه گزینه‌های انتخاب‌شده',
        description: 'مقایسه بر پایه بهترین آفر موجود در همین نتایج؛ قیمت و پذیرش اعتباری مطابق داده ثبت‌شده است.',
        columns: comparisonColumns,
        rows: comparisonRows,
      },
    }]
    : selectedCompareResults.length === 1
      ? [{ type: 'notice', id: 'comparison-next-step', data: { message: 'یک گزینه انتخاب شده است. برای نمایش جدول مقایسه، یک یا دو محصول دیگر هم انتخاب کن.' } }]
      : []

  const quickPrompts = [
    { label: 'لپ‌تاپ برای کار', detail: 'بودجه و مشخصات مهم را مقایسه کن', icon: <Laptop size={18} />, prompt: 'برای برنامه‌نویسی یک لپ‌تاپ مناسب در تهران پیدا کن؛ گزینه‌ها را با قیمت و مزایا مقایسه کن.' },
    { label: 'فشارسنج خانگی', detail: 'مدل‌های مناسب مصرف خانگی', icon: <HeartPulse size={18} />, prompt: 'یک فشارسنج دیجیتال بازویی برای مصرف خانگی در تهران می‌خواهم.' },
    { label: 'هدفون اقتصادی', detail: 'فروشگاه‌های ارزان‌تر را پیدا کن', icon: <Headphones size={18} />, prompt: 'هدفون بی‌سیم اقتصادی در تهران پیدا کن و ارزان‌ترین فروشگاه‌ها را مقایسه کن.' },
    { label: 'خرید اعتباری', detail: 'فقط پیشنهادهای دارای شرط اعتبار ثبت‌شده', icon: <CreditCard size={18} />, prompt: 'یک هدفون بی‌سیم در تهران می‌خواهم؛ فقط گزینه‌های فروشگاه‌هایی را نشان بده که خرید اعتباری حضوری می‌پذیرند.' },
  ]
  const isEmptyConversation = chatMessages.length === 0 && !isRestoring

  return (
    <section className={`conversation-panel${isEmptyConversation ? ' conversation-panel-empty' : ''}`} aria-labelledby="conversation-heading">
      <div className="conversation-panel-header">
        <div className="conversation-header-copy">
          <h2 id={!isEmptyConversation ? 'conversation-heading' : undefined}>گفتگوی خرید</h2>
        </div>
        {chatMessages.length > 0 && <button className="conversation-reset" type="button" disabled={isRunning || isRestoring || contactingOfferId !== null} onClick={startNewMission}><RotateCcw size={15} /> گفتگوی تازه</button>}
      </div>

      <div className="conversation-transcript" aria-label="گفتگوی مأموریت خرید" aria-live="off" aria-busy={isRunning || isRestoring}>
        {isEmptyConversation && (
          <div className="conversation-welcome">
            <h3 id="conversation-heading">چی می‌خوای بخری؟</h3>
            <p>کالا، کاربرد یا بودجه‌ات رو بنویس.</p>
            <div className="quick-prompt-grid">
              {quickPrompts.map((item) => (
                <button type="button" className="quick-prompt" key={item.label} disabled={isRunning || isRestoring} onClick={() => void runTurn(item.prompt)}>
                  <span className="quick-prompt-icon" aria-hidden="true">{item.icon}</span>
                  <span className="quick-prompt-copy"><strong>{item.label}</strong><small>{item.detail}</small></span>
                  <ArrowLeft size={16} className="quick-prompt-arrow" />
                </button>
              ))}
            </div>

          </div>
        )}

        {chatMessages.map((item) => {
          if (item.role === 'user') {
            return <div className="chat-message chat-message-user" key={item.id}><div className="user-bubble">{item.text}</div></div>
          }
          const isCurrent = currentAssistantMessage?.id === item.id
          const preComponents = item.components.filter((component) => PRE_RESULT_COMPONENTS.has(component.type))
          const postComponents = item.components.filter((component) => !PRE_RESULT_COMPONENTS.has(component.type))
          const hasDedicatedEmptyState = item.components.some((component) => ['empty_state', 'clarification_form'].includes(component.type))
          return (
            <article className={`chat-message chat-message-assistant ${item.pending ? 'pending' : ''}`} key={item.id}>
              <div className="assistant-message-heading"><span className="assistant-mini-avatar"><Sparkles size={15} /></span><strong>بازارکامپس</strong>{item.pending && <span className="assistant-working"><i /><i /><i /> در حال بررسی</span>}</div>
              {item.text && (item.results && item.results.length > 0 && !item.pending
                ? <details className="assistant-explanation"><summary>درباره این نتایج <ChevronDown size={13} aria-hidden="true" /></summary><p>{item.text}</p></details>
                : <div className="assistant-message-copy">{item.text}</div>)}
              {preComponents.length > 0 && <GenUIRenderer components={preComponents} defaults={{ query: lastQuery, max_price_toman: budget, must_have_in_person_credit: mustHaveCredit, sort: constraints.sort ?? 'relevance' }} disabled={isRunning || isRestoring || !isCurrent} onAction={handleGenUIAction} />}
              {item.results && item.results.length > 0 && (
                <div className="mission-results-block conversation-results-block">
                  <div className="mission-results-header">
                    <div><h3>نتایج پیشنهادی</h3></div>
                    <div className="mission-results-header-actions">
                      <span>{money.format(item.resultCount ?? item.results.length)} محصول</span>
                      {isCurrent && <button type="button" className="mission-edit-filters" onClick={() => handleGenUIAction({ type: 'open_filter_form' })} disabled={isRunning || isRestoring}><SlidersHorizontal size={15} /> تغییر شرایط</button>}
                    </div>
                  </div>
                  {isCurrent && selectedCompareProductIds.length > 0 && <p className="mission-compare-hint">{money.format(selectedCompareProductIds.length)} گزینه برای مقایسه انتخاب شده؛ حداکثر ۳ گزینه.</p>}
                  {isCurrent && comparisonComponents.length > 0 && <GenUIRenderer components={comparisonComponents} defaults={{ query: lastQuery, max_price_toman: budget, must_have_in_person_credit: mustHaveCredit, sort: constraints.sort ?? 'relevance' }} disabled={isRunning || isRestoring} onAction={handleGenUIAction} />}
                  <ProductResults
                    results={item.results}
                    missionId={missionId ?? ''}
                    onContact={contact}
                    contactingOfferId={contactingOfferId}
                    contactByOffer={contactByOffer}
                    selectedCompareProductIds={isCurrent ? selectedCompareProductIds : []}
                    onToggleCompare={toggleComparedProduct}
                    offerViews={offerViews}
                    onToggleOffers={toggleProductOffers}
                    onLoadMoreOffers={loadMoreProductOffers}
                    allowActions={isCurrent}
                  />
                </div>
              )}
              {item.results && item.results.length === 0 && !hasDedicatedEmptyState && (
                <section className="mission-empty-results" aria-labelledby={`empty-heading-${item.id}`}>
                  <div className="mission-empty-copy"><strong id={`empty-heading-${item.id}`}>با این شرایط محصولی پیدا نشد</strong><p role="status">می‌توانی عبارت جست‌وجو را ویرایش کنی یا یکی از فیلترهای اختیاری را تغییر بدهی. شروط الزامی بدون انتخاب تو حذف نمی‌شوند.</p></div>
                  {isCurrent && <div className="mission-empty-actions">
                    <button type="button" className="mission-empty-primary" onClick={() => handleGenUIAction({ type: 'open_filter_form' })} disabled={isRunning || isRestoring}><SlidersHorizontal size={15} /> تغییر شرایط</button>
                    <button type="button" className="mission-empty-secondary" onClick={() => handleGenUIAction({ type: 'fill_query', query: lastQuery })} disabled={isRunning || isRestoring}>ویرایش عبارت جست‌وجو</button>
                  </div>}
                </section>
              )}
              {postComponents.length > 0 && <GenUIRenderer components={postComponents} defaults={{ query: lastQuery, max_price_toman: budget, must_have_in_person_credit: mustHaveCredit, sort: constraints.sort ?? 'relevance' }} disabled={isRunning || isRestoring || !isCurrent} onAction={handleGenUIAction} />}
            </article>
          )
        })}
        {isRestoring && <div className="conversation-inline-state"><LoaderCircle className="spin" size={17} /> در حال بازیابی گفتگوی قبلی…</div>}
        {events.some((event) => ['stage', 'turn.completed', 'contact.completed'].includes(event.type)) && (
          <details className="mission-event-details conversation-event-details">
            <summary>روند بررسی و شفافیت نتایج</summary>
            <ol>{events.filter((event) => ['stage', 'turn.completed', 'contact.completed'].includes(event.type)).map((event) => {
              const description = describeMissionEvent(event)
              if (!description) return null
              return <li key={event.seq}><CheckCircle2 size={14} /><div><strong>{description.title}</strong>{description.detail && <small>{description.detail}</small>}</div></li>
            })}</ol>
          </details>
        )}
        <div ref={transcriptEndRef} />
      </div>

      {error && <div className="conversation-error" role="alert"><AlertCircle size={17} /><span>{error}</span><button type="button" onClick={() => setError(null)}>بستن</button></div>}
      {isRunning && <div className="conversation-running-note" role="status" aria-live="polite"><span className="mission-progress-dot" />{stageLabel ?? 'در حال بررسی درخواست'}<span className="conversation-running-sub">اطلاعات محصول و شروط خرید در حال بررسی است</span></div>}

      <form className="conversation-composer" id="conversation-composer" onSubmit={submit}>
        {lastQuery && <button className="composer-tool" type="button" aria-label="تنظیم شرایط خرید" title="تنظیم شرایط خرید" disabled={isRunning || isRestoring} onClick={() => handleGenUIAction({ type: 'open_filter_form' })}><SlidersHorizontal size={18} /></button>}
        <button className={`composer-tool ${location ? 'location-active' : ''}`} type="button" aria-label={location ? 'حذف موقعیت' : 'استفاده از موقعیت فعلی'} title={location ? 'حذف فیلتر موقعیت' : 'مرتب‌سازی فروشگاه‌ها بر اساس فاصله از موقعیت فعلی'} disabled={isRunning || isRestoring || isLocating} onClick={handleLocationClick}>{isLocating ? <LoaderCircle size={18} className="spin" /> : location ? <MapPinOff size={18} /> : <LocateFixed size={18} />}</button>
        <textarea
          ref={composerInputRef}
          aria-label="پیام به دستیار خرید"
          rows={1}
          maxLength={2000}
          value={message}
          disabled={isRunning || isRestoring}
          onChange={(event) => setMessage(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault()
              event.currentTarget.form?.requestSubmit()
            }
          }}
          placeholder="مثلاً تا ۳ میلیون تومان یک هدفون مناسب برای رفت‌وآمد پیدا کن…"
        />
        <button className="composer-send" type="submit" aria-label="ارسال پیام" title="ارسال پیام" disabled={!message.trim() || isRunning || isRestoring}>
          {isRunning ? <LoaderCircle size={18} className="spin" /> : <Send size={17} />}
        </button>
      </form>
      
      <div className="conversation-bottom-row">
        <div className="mission-context-row">
          {formatBudgetLabel(budget) && <span>بودجه: {formatBudgetLabel(budget)}</span>}
          {mustHaveCredit && <span>خرید اعتباری حضوری</span>}
          {location && <span><MapPin size={13} /> فاصله مستقیم تا {money.format(radiusM / 1000)} کیلومتر</span>}
          {isLocating && <span><LoaderCircle size={13} className="spin" /> دریافت موقعیت…</span>}
        </div>
        <details className="conversation-disclosure">
          <summary>درباره داده‌ها</summary>
          <p>قیمت‌ها تاریخی‌اند و موجودی به‌صورت نمایشی بررسی می‌شود. بیشتر نام فروشگاه‌ها و همه شماره‌های تماس دیتاست مسابقه ساختگی‌اند.</p>
        </details>
      </div>
    </section>
  )
}
