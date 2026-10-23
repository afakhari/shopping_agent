import { useEffect, useRef, useState, type FormEvent } from 'react'
import { AlertCircle, ArrowLeft, CheckCircle2, ChevronDown, ChevronUp, Clock3, CreditCard, ExternalLink, Headphones, Laptop, LoaderCircle, LocateFixed, MapPin, MapPinOff, Send, ShieldCheck, SlidersHorizontal, Sparkles, Store, RotateCcw, X } from 'lucide-react'
import { getProductOffers, type CatalogOffer, type CatalogSearchResult, type ProductOffersResponse } from '../search/catalog-api'
import { buildComparisonSpecColumns } from './comparison-specs'
import { classifyLocalConversation, localConversationReply } from './greeting-intent'
import { completedTurnWasPersisted } from './recovery-state'
import { findCurrentSearchMessage, shouldFollowConversation } from './conversation-behavior'
import { GenUIRenderer } from './GenUIRenderer'
import { formatDistance, formatLastPriceChange, getPriceQualityLabel, openStreetMapUrl } from './ui-formatters'
import { osmEmbedUrl, TEHRAN_REGION_SAMPLES } from './shop-map'
import { getResultPayload, getUIComponents, type GenUIAction, type GenUIComponent } from './genui-types'
import { resolveRecoveryOffer } from './recovery-options'
import { chooseProductHighlights } from './product-highlights'
import { ActiveShoppingFilters } from './ActiveShoppingFilters'
import { sellerHighlights } from './seller-highlights'
import { formatCatalogPrice } from './catalog-pricing'
import {
  createContactAttempt,
  createMission,
  getMission,
  isProductResultPayload,
  sendMissionTurn,
  updateMissionFocus,
  type ContactAttemptResponse,
  type ContactAttemptRecord,
  type MissionConstraints,
  type MissionEvent,
  type MissionFocusAction,
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
  return formatCatalogPrice(price)
}

function formatRegisteredWarranty(warranty: CatalogOffer['warranty']): string | null {
  if (!warranty) return null
  const provider = typeof warranty.provider === 'string' ? warranty.provider.trim() : ''
  const period = Number.isFinite(warranty.period_months) && Number(warranty.period_months) > 0
    ? `${money.format(warranty.period_months!)} ماه`
    : ''
  const description = typeof warranty.description === 'string' ? warranty.description.trim() : ''
  return [provider, period, description].filter(Boolean).join('، ') || null
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
    const facts = []
    if (typeof total === 'number' && Number.isFinite(total)) {
      facts.push(`${money.format(total)} محصول با شروط جاری بررسی شد`)
    }
    const parser = readText(event.payload, 'intent_parser')
    if (parser === 'llm') facts.push('نیت خرید با مدل تحلیل شد')
    else if (parser === 'heuristic') facts.push('نیت خرید با روش قاعده‌محور تحلیل شد')
    const detail = facts.join('؛ ')
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
  onSelectProduct,
  selectedProductId,
  selectedOfferId,
  onSelectOffer,
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
  onSelectProduct: (productId: string) => void
  selectedProductId: string | null
  selectedOfferId: string | null
  onSelectOffer: (offerId: string) => void
  offerViews: Record<string, ProductOfferView>
  onToggleOffers: (result: CatalogSearchResult) => void
  onLoadMoreOffers: (result: CatalogSearchResult) => void
  allowActions?: boolean
}) {
  const [showAllResults, setShowAllResults] = useState(false)
  const [openMapOfferId, setOpenMapOfferId] = useState<string | null>(null)
  if (results.length === 0) return <p className="mission-empty-results">با این عبارت و شرایط، محصول واجد شرایطی پیدا نشد. می‌توانی عبارت یا شروط خرید را تغییر بدهی.</p>
  const visibleResults = showAllResults ? results : results.slice(0, 4)
  return (
    <div className="mission-product-results" aria-label="نتایج محصولات">
      {visibleResults.map((result, productIndex) => {
        const offer = result.best_offer
        const contact = contactByOffer[offer.id]
        const offerView = offerViews[result.product.id]
        const relativeTags = sellerHighlights(offerView?.offers ?? [])
        const offersPanelId = `seller-offers-${result.product.id.replace(/[^a-zA-Z0-9_-]/g, '-')}`
        const imageUrl = result.product.images.find((value) => /^https?:\/\//i.test(value))
        const address = offer.shop.address ?? offer.shop.location_label ?? 'نشانی ثبت نشده'
        const priceUpdatedAt = formatPersianDateTime(offer.last_price_changed_at)
        const priceUpdatedRelative = formatLastPriceChange(offer.last_price_changed_at)
        const distanceLabel = formatDistance(offer.shop.distance_m)
        const mapUrl = openStreetMapUrl(offer.shop.lat, offer.shop.lon)
        const isCompared = selectedCompareProductIds.includes(result.product.id)
        const isSelected = selectedProductId === result.product.id
        const highlights = chooseProductHighlights(result.product)
        return (
          <article className={`mission-product-card ${isCompared ? 'is-compared' : ''} ${allowActions && offerView?.expanded ? 'is-offers-expanded' : ''}`} key={result.product.id}>
            <div className="mission-product-image">
              <ProductThumbnail src={imageUrl} title={result.product.title} />
            </div>
            <div className="mission-product-main">
              <div className="mission-product-heading-row">
                {productIndex < 4 && <span className="mission-product-rank" aria-label={`مدل شماره ${productIndex + 1}`}>{money.format(productIndex + 1)}</span>}
                <strong title={result.product.title}>{result.product.title}</strong>
                {isSelected && <span className="mission-compared-badge"><CheckCircle2 size={13} /> مدل منتخب</span>}
                {isCompared && !isSelected && <span className="mission-compared-badge"><CheckCircle2 size={13} /> برای مقایسه</span>}
              </div>
              <div className="mission-product-price-line">
                <strong className="mission-product-price">{formatPrice(offer.price_toman)}</strong>
                <span className="mission-product-seller"><Store size={13} aria-hidden="true" />{offer.shop.name}</span>
              </div>
              <div className="mission-product-meta">
                <span className={`mission-price-quality ${offer.price_quality}`}><i />{getPriceQualityLabel(offer.price_quality)}</span>
                <span className="mission-offer-count"><Store size={13} />{money.format(result.eligible_offers_count)} فروشگاه</span>
                {offer.in_person_credit_eligible && (
                  <span className="mission-credit-confirmed"><CreditCard size={12} /> اعتباری</span>
                )}
              </div>
              {highlights.length > 0 && <dl className="mission-product-highlights" aria-label="مشخصات مهم ثبت‌شده">
                {highlights.map((item) => (
                  <div key={item.key}><dt>{item.key}</dt><dd>{item.value}</dd></div>
                ))}
              </dl>}
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
                  {formatRegisteredWarranty(offer.warranty) && <small>گارانتی ثبت‌شده: {formatRegisteredWarranty(offer.warranty)}</small>}
                  <small className="mission-product-address"><MapPin size={13} aria-hidden="true" />{address}</small>
                  {offer.shop.opening_status && <small>ساعات ثبت‌شده: {offer.shop.opening_status.label} (نه تأیید لحظه‌ای)</small>}
                  {offer.shop.indoor_hints && [offer.shop.indoor_hints.mall, offer.shop.indoor_hints.floor, offer.shop.indoor_hints.unit].filter(Boolean).length > 0 && (
                    <small>راهنمای نشانی: {[offer.shop.indoor_hints.mall, offer.shop.indoor_hints.floor, offer.shop.indoor_hints.unit].filter(Boolean).join('، ')}</small>
                  )}
                  {distanceLabel && <small className="mission-product-distance"><LocateFixed size={13} aria-hidden="true" />فاصلهٔ مستقیم: {distanceLabel}</small>}
                  {mapUrl && <a className="mission-map-link" href={mapUrl} target="_blank" rel="noopener noreferrer">
                    <MapPin size={13} aria-hidden="true" /> نمایش موقعیت ثبت‌شده روی نقشه <ExternalLink size={12} aria-hidden="true" />
                  </a>}
                  {!offer.in_person_credit_eligible && (
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
                {allowActions && productIndex < 4 && (
                  <button type="button" className="mission-select-button" aria-pressed={isSelected}
                    onClick={() => onSelectProduct(result.product.id)}>
                    <CheckCircle2 size={15} /> {isSelected ? 'مدل منتخب' : 'انتخاب مدل'}
                  </button>
                )}
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
                  {offerView.offers.length > 1 && (
                    <p className="mission-offer-shortlist-note">برچسب‌های مقایسه فقط بین فروشگاه‌های بارگذاری‌شده هستند؛ فاصله‌ها مستقیم و ساعت کار طبق داده ثبت‌شده است.</p>
                  )}
                  {offerView.offers.map((sellerOffer, offerIndex) => {
                    const attempt = contactByOffer[sellerOffer.id]
                    const sellerDistance = formatDistance(sellerOffer.shop.distance_m)
                    const sellerUpdatedAt = formatPersianDateTime(sellerOffer.last_price_changed_at)
                    const sellerMapUrl = openStreetMapUrl(sellerOffer.shop.lat, sellerOffer.shop.lon)
                    const inlineMapUrl = osmEmbedUrl(sellerOffer.shop.lat, sellerOffer.shop.lon)
                    return (
                      <article className="mission-offer-row" key={sellerOffer.id}>
                        <div className="mission-offer-copy">
                          <button type="button" className="mission-select-button"
                            aria-pressed={selectedOfferId === sellerOffer.id}
                            onClick={() => onSelectOffer(sellerOffer.id)}>
                            {money.format(offerIndex + 1)}. {selectedOfferId === sellerOffer.id ? 'فروشنده منتخب' : 'انتخاب فروشنده'}
                          </button>
                          <div className="mission-seller-heading">
                            <strong>{sellerOffer.shop.name}</strong>
                            <span className="mission-offer-price">{formatPrice(sellerOffer.price_toman)}</span>
                          </div>
                          <div className="mission-seller-quick-facts">
                            {sellerOffer.id === relativeTags.cheapestOfferId && <span className="mission-seller-tag">ارزان‌ترین در فهرست</span>}
                            {sellerOffer.id === relativeTags.closestOfferId && <span className="mission-seller-tag">نزدیک‌ترین در فهرست</span>}
                            {sellerDistance && <span><LocateFixed size={12} aria-hidden="true" />{sellerDistance} فاصله مستقیم</span>}
                            {sellerOffer.in_person_credit_eligible && <span><CreditCard size={12} aria-hidden="true" />اعتبار حضوری این آفر</span>}
                          </div>
                          <div className="mission-offer-badges">
                            <span className={`mission-price-quality ${sellerOffer.price_quality}`}><i />{getPriceQualityLabel(sellerOffer.price_quality)}</span>
                            {sellerOffer.shop.opening_status && <span>{sellerOffer.shop.opening_status.label}</span>}
                          </div>
                          <details className="mission-seller-details">
                            <summary>آدرس، گارانتی و اطلاعات تکمیلی</summary>
                            <div>
                              {sellerOffer.seller_title && <small>عنوان فروشنده: {sellerOffer.seller_title}</small>}
                              {formatRegisteredWarranty(sellerOffer.warranty) && <small>گارانتی ثبت‌شده: {formatRegisteredWarranty(sellerOffer.warranty)}</small>}
                              <small><MapPin size={12} aria-hidden="true" />{sellerOffer.shop.address ?? sellerOffer.shop.location_label ?? 'نشانی ثبت نشده'}</small>
                              {sellerOffer.shop.indoor_hints && [sellerOffer.shop.indoor_hints.mall, sellerOffer.shop.indoor_hints.floor, sellerOffer.shop.indoor_hints.unit].filter(Boolean).length > 0 && (
                                <small>داخل مجتمع: {[sellerOffer.shop.indoor_hints.mall, sellerOffer.shop.indoor_hints.floor, sellerOffer.shop.indoor_hints.unit].filter(Boolean).join('، ')}</small>
                              )}
                              <small>اعتبار حضوری: {sellerOffer.in_person_credit_eligible ? 'برای این آفر ثبت‌شده' : 'برای این آفر ثبت نشده'}</small>
                              {sellerUpdatedAt && <small><Clock3 size={12} aria-hidden="true" />آخرین تغییر قیمت ثبت‌شده: {sellerUpdatedAt}</small>}
                              {sellerMapUrl && <a className="mission-offer-map" href={sellerMapUrl} target="_blank" rel="noopener noreferrer"><MapPin size={12} /> موقعیت روی نقشه <ExternalLink size={11} /></a>}
                              {inlineMapUrl && <button className="mission-inline-map-toggle" type="button" aria-expanded={openMapOfferId === sellerOffer.id} onClick={() => setOpenMapOfferId(current => current === sellerOffer.id ? null : sellerOffer.id)}>
                                <MapPin size={12} />{openMapOfferId === sellerOffer.id ? 'بستن نقشه' : 'نقشه در همین صفحه'}
                              </button>}
                            </div>
                          </details>
                        </div>
                        {inlineMapUrl && openMapOfferId === sellerOffer.id && (
                          <div className="mission-inline-map" role="region" aria-label={`پیش‌نمایش نقشه فروشگاه ${sellerOffer.shop.name}`}>
                            <iframe src={inlineMapUrl} title={`موقعیت ثبت‌شده ${sellerOffer.shop.name} روی OpenStreetMap`} loading="lazy" referrerPolicy="no-referrer" />
                            <small>مختصات ثبت‌شده فروشگاه؛ زمان سفر و مسیر داخل پاساژ تأیید نشده‌اند.</small>
                          </div>
                        )}
                        <button
                          type="button"
                          className="mission-offer-verify"
                          onClick={() => onContact({ ...result, best_offer: sellerOffer })}
                          disabled={contactingOfferId === sellerOffer.id || !missionId}
                        >
                          {contactingOfferId === sellerOffer.id ? <LoaderCircle size={15} className="spin" /> : <ShieldCheck size={15} />}
                          {contactingOfferId === sellerOffer.id ? 'در حال بررسی…' : 'استعلام آزمایشی فروشنده'}
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

export function rebuildChatFromEvents(events: MissionEvent[]): MissionChatMessage[] {
  const messages: MissionChatMessage[] = []
  let awaitingAssistant = false
  let currentSocialIntent: ReturnType<typeof classifyLocalConversation> = null
  for (const event of [...events].sort((left, right) => left.seq - right.seq)) {
    if (event.type === 'user.message') {
      const value = readText(event.payload, 'message')
      if (value) messages.push({ id: `user-${event.seq}`, role: 'user', text: value, components: [] })
      currentSocialIntent = classifyLocalConversation(value ?? '')
      awaitingAssistant = true
      continue
    }
    if (event.type === 'assistant.message') {
      const value = readText(event.payload, 'text')
      if (value) messages.push({
        id: `assistant-${event.seq}`, role: 'assistant',
        text: currentSocialIntent ? localConversationReply(currentSocialIntent) : value,
        components: [],
      })
      awaitingAssistant = false
      continue
    }
    if (event.type === 'ui.component') {
      // Older app versions incorrectly produced product cards for smalltalk.
      // Suppress those obsolete cards on replay, not the persisted event itself.
      if (currentSocialIntent && getUIComponents(event).some((component) =>
        PRIMARY_SEARCH_COMPONENTS.has(component.type))) continue
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
  const [comparisonOpen, setComparisonOpen] = useState(false)
  const [isRunning, setIsRunning] = useState(false)
  const [contactingOfferId, setContactingOfferId] = useState<string | null>(null)
  const [contactByOffer, setContactByOffer] = useState<Record<string, ContactAttemptResponse>>({})
  const [offerViews, setOfferViews] = useState<Record<string, ProductOfferView>>({})
  const [brandFilter, setBrandFilter] = useState<string | null>(null)
  const [modelFilter, setModelFilter] = useState<string | null>(null)
  const [selectedProductId, setSelectedProductId] = useState<string | null>(null)
  const [selectedOfferId, setSelectedOfferId] = useState<string | null>(null)
  const [resultSetId, setResultSetId] = useState<string | null>(null)
  const resultSetIdRef = useRef<string | null>(null)
  const [resultsStale, setResultsStale] = useState(false)
  const [queuePaused, setQueuePaused] = useState(false)
  const queuePausedRef = useRef(false)
  const latestEventSeqRef = useRef(0)
  const missionIdRef = useRef<string | null>(missionId)
  const serverConstraintsRef = useRef<MissionConstraints | null>(null)
  const queuedTurnsRef = useRef<Array<{ text: string; constraints: MissionConstraints; displayQuery: string }>>([])
  const [queuedCount, setQueuedCount] = useState(0)
  const [activeFilterForm, setActiveFilterForm] = useState<GenUIComponent | null>(null)
  const filterDialogRef = useRef<HTMLDialogElement | null>(null)
  const transcriptRef = useRef<HTMLDivElement | null>(null)
  const shouldAutoScrollRef = useRef(true)
  const offerRequestControllers = useRef(new Map<string, AbortController>())
  const [error, setError] = useState<string | null>(null)
  const [stageLabel, setStageLabel] = useState<string | null>(null)
  const [isLocating, setIsLocating] = useState(false)
  const [showRegionPicker, setShowRegionPicker] = useState(false)
  const [selectedRegionId, setSelectedRegionId] = useState('')
  const composerInputRef = useRef<HTMLTextAreaElement | null>(null)
  const turnCounter = useRef(0)
  const turnInFlightRef = useRef(false)
  const contactInFlightRef = useRef(false)
  // Retain a request ID after a network failure, so a user-triggered retry
  // receives the original server simulation instead of creating a duplicate.
  const pendingContactIdsRef = useRef(new Map<string, string>())

  const constraints: MissionConstraints = {
    city: 'tehran',
    ...(budget.trim() ? { max_price_toman: budget.trim() } : {}),
    must_have_in_person_credit: mustHaveCredit,
    brand_name: brandFilter,
    model_exact: modelFilter,
    sort: location || sort !== 'distance_asc' ? sort : 'relevance',
    ...(location ? { lat: location.lat, lon: location.lon, radius_m: radiusM } : {}),
  }

  const currentAssistantMessage = [...chatMessages].reverse().find((item) => item.role === 'assistant')
  // A follow-up answer without a catalog payload must not erase product selection.
  const currentResultsMessage = findCurrentSearchMessage(chatMessages)
  const results = currentResultsMessage?.results ?? []

  useEffect(() => {
    const restoreId = initialMissionId
    if (!restoreId) return

    const controller = new AbortController()
    void getMission(restoreId, controller.signal)
      .then((snapshot) => {
        const history = snapshot.events ?? []
        setEvents(history)
        latestEventSeqRef.current = Math.max(0, ...history.map((item) => item.seq))
        resultSetIdRef.current = typeof snapshot.state?.result_set_id === 'string' ? snapshot.state.result_set_id : null
        setResultSetId(resultSetIdRef.current)
        setResultsStale(snapshot.state?.results_stale === true)
        setSelectedOfferId(typeof snapshot.state?.selected_offer_id === 'string' ? snapshot.state.selected_offer_id : null)
        serverConstraintsRef.current = snapshot.constraints
        setBrandFilter(snapshot.constraints.brand_name ?? null)
        setModelFilter(snapshot.constraints.model_exact ?? null)
        missionIdRef.current = restoreId
        setSelectedProductId(typeof snapshot.state?.selected_product_id === 'string' ? snapshot.state.selected_product_id : null)
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
        const restoredQuery = restoredProductQuery
          ?? (classifyLocalConversation(restoredMessage) ? '' : restoredMessage)
        setLastQuery(restoredQuery)
        onRestoreConstraints(snapshot.constraints, restoredQuery)
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
    const transcript = transcriptRef.current
    if (transcript && shouldAutoScrollRef.current) {
      transcript.scrollTop = transcript.scrollHeight
    }
  }, [chatMessages, isRunning])

  useEffect(() => {
    const dialog = filterDialogRef.current
    if (!dialog) return
    if (activeFilterForm && !dialog.open) dialog.showModal()
    if (!activeFilterForm && dialog.open) dialog.close()
  }, [activeFilterForm])

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
    latestEventSeqRef.current = Math.max(latestEventSeqRef.current, event.seq)
    if (event.type === 'focus.updated') {
      setSelectedProductId(typeof event.payload.selected_product_id === 'string' ? event.payload.selected_product_id : null)
      setSelectedOfferId(typeof event.payload.selected_offer_id === 'string' ? event.payload.selected_offer_id : null)
    }
    if (event.type === 'turn.completed') {
      if (typeof event.payload.result_set_id === 'string') {
        resultSetIdRef.current = event.payload.result_set_id
        setResultSetId(event.payload.result_set_id)
      }
      if (typeof event.payload.results_stale === 'boolean') setResultsStale(event.payload.results_stale)
      if (Object.prototype.hasOwnProperty.call(event.payload, 'selected_offer_id')) {
        setSelectedOfferId(typeof event.payload.selected_offer_id === 'string' ? event.payload.selected_offer_id : null)
      }
    }
    setEvents((current) => current.some((saved) => saved.seq === event.seq)
      ? current
      : [...current, event].sort((left, right) => left.seq - right.seq))

    if (event.type === 'turn.completed' && Object.prototype.hasOwnProperty.call(event.payload, 'selected_product_id')) {
      setSelectedProductId(typeof event.payload.selected_product_id === 'string' ? event.payload.selected_product_id : null)
    }
    if (event.type === 'turn.completed' && isRecord(event.payload.constraints)) {
      serverConstraintsRef.current = event.payload.constraints as MissionConstraints
      setBrandFilter(serverConstraintsRef.current.brand_name ?? null)
      setModelFilter(serverConstraintsRef.current.model_exact ?? null)
      // Reconcile inferred natural-language constraints with the visible filters.
      // The server decides eligibility; the client must not silently present stale filters.
      const interpreted = readText(event.payload, 'search_query') || lastQuery
      onRestoreConstraints(event.payload.constraints as MissionConstraints, interpreted)
    }
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
        setSelectedProductId(null)
        setSelectedOfferId(null)
        setComparisonOpen(false)
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

  const applyFocus = async (input: Omit<MissionFocusAction, 'result_set_id'>) => {
    const activeId = missionIdRef.current
    const activeResultId = resultSetIdRef.current ?? resultSetId
    if (isRunning || isRestoring || turnInFlightRef.current || resultsStale || !activeId || !activeResultId) {
      setError('نتایج این جست‌وجو آماده یا معتبر نیستند؛ ابتدا وضعیت را به‌روز کن.')
      return
    }
    try {
      const response = await updateMissionFocus(activeId, { ...input, result_set_id: activeResultId })
      response.events.forEach(handleEvent)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'انتخاب ثبت نشد؛ وضعیت مأموریت را بررسی کن.')
    }
  }

  const removeQueuedTurn = (index: number, edit: boolean) => {
    const item = queuedTurnsRef.current[index]
    if (!item) return
    queuedTurnsRef.current.splice(index, 1)
    setQueuedCount(queuedTurnsRef.current.length)
    if (edit) {
      setMessage(item.text)
      composerInputRef.current?.focus()
    }
  }

  const resumeQueue = () => {
    if (isRunning || isRestoring || turnInFlightRef.current) return
    queuePausedRef.current = false
    setQueuePaused(false)
    const next = queuedTurnsRef.current.shift()
    setQueuedCount(queuedTurnsRef.current.length)
    if (next) void runTurn(next.text, serverConstraintsRef.current ?? next.constraints, next.displayQuery)
  }

  const runTurn = async (turnMessage: string, turnConstraints: MissionConstraints = constraints, displayQuery = turnMessage) => {
    const trimmed = turnMessage.trim()
    // The ref is synchronous: two Enter clicks in the same React render cannot
    // launch duplicate POSTs or two paid model requests.
    if (!trimmed) return
    if (isRunning || isRestoring || turnInFlightRef.current || queuePausedRef.current) {
      if (queuedTurnsRef.current.length >= 5) {
        setError('حداکثر پنج پیام در صف است. پس از پردازش آن‌ها پیام جدید بفرست.')
        return
      }
      queuedTurnsRef.current.push({ text: trimmed, constraints: { ...turnConstraints }, displayQuery })
      setQueuedCount(queuedTurnsRef.current.length)
      setMessage('')
      return
    }
    shouldAutoScrollRef.current = true

    const localIntent = classifyLocalConversation(trimmed)
    if (localIntent) {
      turnCounter.current += 1
      const localId = `local-${Date.now()}-${turnCounter.current}`
      setChatMessages((current) => [
        ...current,
        { id: `user-${localId}`, role: 'user', text: trimmed, components: [] },
        { id: `assistant-${localId}`, role: 'assistant', text: localConversationReply(localIntent), components: [] },
      ])
      setMessage('')
      setError(null)
      return
    }

    turnInFlightRef.current = true
    setError(null)
    setIsRunning(true)
    setStageLabel('در حال آماده‌سازی مأموریت خرید...')
    if (!results.length) setLastQuery(displayQuery.trim())
    turnCounter.current += 1
    const turnId = `${Date.now()}-${turnCounter.current}`
    const lastSavedSequence = latestEventSeqRef.current
    let activeMissionId: string | null = missionIdRef.current
    let startedServerTurn = false
    let confirmed = false
    setChatMessages((current) => [
      ...current,
      { id: `user-${turnId}`, role: 'user', text: trimmed, components: [] },
      { id: `assistant-${turnId}`, role: 'assistant', text: 'در حال تحلیل درخواست و بررسی آفرهای تهران…', components: [], pending: true },
    ])
    setMessage('')
    try {
      if (!activeMissionId) {
        const created = await createMission(trimmed, turnConstraints)
        activeMissionId = created.mission_id
        setMissionId(activeMissionId)
        missionIdRef.current = activeMissionId
        storeMissionId(activeMissionId)
      }
      startedServerTurn = true
      await sendMissionTurn(activeMissionId, trimmed, turnConstraints, handleEvent)
      confirmed = true
    } catch (reason) {
      // A response stream can disconnect AFTER Django commits the turn.
      // Restore that saved turn instead of suggesting a duplicate submission.
      let recovered = false
      if (startedServerTurn && activeMissionId) {
        try {
          const snapshot = await getMission(activeMissionId)
          if (completedTurnWasPersisted(snapshot, trimmed, lastSavedSequence)) {
            const history = snapshot.events ?? []
            setEvents(history)
            latestEventSeqRef.current = Math.max(latestEventSeqRef.current, ...history.map(item => item.seq))
            serverConstraintsRef.current = snapshot.constraints
            setBrandFilter(snapshot.constraints.brand_name ?? null)
            setModelFilter(snapshot.constraints.model_exact ?? null)
            resultSetIdRef.current = typeof snapshot.state?.result_set_id === 'string' ? snapshot.state.result_set_id : null
            setResultSetId(resultSetIdRef.current)
            setResultsStale(snapshot.state?.results_stale === true)
            setSelectedProductId(typeof snapshot.state?.selected_product_id === 'string' ? snapshot.state.selected_product_id : null)
            setSelectedOfferId(typeof snapshot.state?.selected_offer_id === 'string' ? snapshot.state.selected_offer_id : null)
            setChatMessages(rebuildChatFromEvents(history))
            setContactByOffer(restoreContactResponses(history))
            const actualQuery = typeof snapshot.state?.search_query === 'string'
              ? snapshot.state.search_query : displayQuery
            setLastQuery(actualQuery)
            onRestoreConstraints(snapshot.constraints, actualQuery)
            setStageLabel('نتیجه ثبت‌شده مأموریت از سرور بازیابی شد.')
            recovered = true
            confirmed = true
          }
        } catch {
          // Do not mask the original error; an offline network may block GET too.
        }
      }
      if (!recovered) {
        const rawError = reason instanceof Error ? reason.message : 'ارتباط با سرور برقرار نشد.'
        const errorText = startedServerTurn
          ? `${rawError} ممکن است درخواست در سرور ثبت شده باشد؛ قبل از تکرار، «بازیابی وضعیت» را بزن.`
          : rawError
        setError(errorText)
        setMessage((current) => current.trim() ? current : trimmed)
        setChatMessages((current) => {
          const next = [...current]
          const index = findLastPendingAssistantIndex(next)
          if (index >= 0 && next[index]) next[index] = {
            ...next[index]!, text: 'پاسخ کامل دریافت نشد. متن درخواستت در کادر باقی مانده؛ می‌توانی وضعیت را بازیابی یا درخواست را ویرایش کنی.', pending: false,
          }
          return next
        })
      }
    } finally {
      turnInFlightRef.current = false
      setIsRunning(false)
      setChatMessages((current) => {
        const next = [...current]
        const index = findLastPendingAssistantIndex(next)
        if (index >= 0 && next[index]) {
          next[index] = { ...next[index]!, text: 'پاسخ کامل دریافت نشد؛ وضعیت ثبت‌شده را بررسی کن.', pending: false }
        }
        return next
      })
      if (confirmed && !queuePausedRef.current) {
        const queued = queuedTurnsRef.current.shift()
        if (queued) {
          setQueuedCount(queuedTurnsRef.current.length)
          Promise.resolve().then(() => {
            void runTurn(queued.text, serverConstraintsRef.current ?? queued.constraints, queued.displayQuery)
          })
        }
      } else if (!confirmed) {
        // Every uncertain failure pauses pending work even if no queue exists yet.
        queuePausedRef.current = true
        setQueuePaused(true)
      }
    }
  }

  const restoreLatestMission = async () => {
    if (!missionId || isRunning || isRestoring) return
    setIsRestoring(true)
    try {
      const snapshot = await getMission(missionId)
      const history = snapshot.events ?? []
      setEvents(history)
      latestEventSeqRef.current = Math.max(latestEventSeqRef.current, ...history.map(item => item.seq))
      resultSetIdRef.current = typeof snapshot.state?.result_set_id === 'string' ? snapshot.state.result_set_id : null
      setResultSetId(resultSetIdRef.current)
      setResultsStale(snapshot.state?.results_stale === true)
      setSelectedOfferId(typeof snapshot.state?.selected_offer_id === 'string' ? snapshot.state.selected_offer_id : null)
      serverConstraintsRef.current = snapshot.constraints
      setBrandFilter(snapshot.constraints.brand_name ?? null)
      setModelFilter(snapshot.constraints.model_exact ?? null)
      setSelectedProductId(typeof snapshot.state?.selected_product_id === 'string' ? snapshot.state.selected_product_id : null)
      setChatMessages(rebuildChatFromEvents(history))
      setContactByOffer(restoreContactResponses(history))
      const rawQuery = typeof snapshot.state?.search_query === 'string'
        ? snapshot.state.search_query : lastQuery
      const latestQuery = classifyLocalConversation(rawQuery) ? '' : rawQuery
      setLastQuery(latestQuery)
      onRestoreConstraints(snapshot.constraints, latestQuery)
      setError(null)
      setStageLabel('آخرین وضعیت ذخیره‌شده بازیابی شد. درخواست ناقص خودکار تکرار نمی‌شود.')
    } catch (reason) {
      setError(reason instanceof Error
        ? `بازیابی فعلاً ممکن نیست: ${reason.message}`
        : 'بازیابی فعلاً ممکن نیست. دوباره به اینترنت متصل شو.')
    } finally {
      setIsRestoring(false)
    }
  }

  const applyManualRegion = (regionId: string) => {
    if (isLocating || isRunning || isRestoring) return
    const area = TEHRAN_REGION_SAMPLES.find((item) => item.id === regionId)
    if (!area) return
    const nextLocation = { lat: area.lat, lon: area.lon }
    const nextConstraints: MissionConstraints = {
      city: 'tehran',
      ...(budget.trim() ? { max_price_toman: budget.trim() } : {}),
      must_have_in_person_credit: mustHaveCredit,
      lat: nextLocation.lat,
      lon: nextLocation.lon,
      radius_m: radiusM,
      sort: 'distance_asc',
    }
    setSelectedRegionId(regionId)
    onLocationChange(nextLocation)
    onRestoreConstraints(nextConstraints, lastQuery)
    setShowRegionPicker(false)
    setError(null)
    setChatMessages((current) => [...current, {
      id: `assistant-manual-location-${Date.now()}`,
      role: 'assistant',
      text: `محدوده نمونه «${area.label}» انتخاب شد. فاصله‌ها مستقیم‌اند و بر اساس مختصات نمونهٔ فروشگاه‌های این محدوده محاسبه می‌شوند.`,
      components: [],
    }])
    if (lastQuery.trim()) void runTurn(lastQuery, nextConstraints, lastQuery)
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
      setSelectedRegionId('')
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
        setSelectedRegionId('')
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
    const exists = selectedCompareProductIds.includes(result.product.id)
    if (!exists && selectedCompareProductIds.length >= 3) {
      setError('حداکثر سه مدل را می‌توانی هم‌زمان مقایسه کنی. یکی را از انتخاب خارج کن.')
      return
    }
    const next = exists
      ? selectedCompareProductIds.filter((id) => id !== result.product.id)
      : [...selectedCompareProductIds, result.product.id]
    setSelectedCompareProductIds(next)
    setComparisonOpen(next.length >= 2)
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
      // Persist the *ordered* rendered seller IDs so "دومی" refers to
      // this list, not to the second product in the previous search.
      // The backend revalidates each offer against current hard filters.
      const listed = append
        ? [...(offerViews[productId]?.offers ?? []), ...response.results].filter(
            (offer, index, all) => all.findIndex((candidate) => candidate.id === offer.id) === index
          )
        : response.results
      await applyFocus({
        action: 'view_sellers',
        product_id: productId,
        offer_ids: listed.slice(0, 24).map((offer) => offer.id),
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
      void applyFocus({ action: 'view_products' })
      return
    }
    if (current?.offers.length && !current.error) {
      setOfferViews((views) => ({ ...views, [result.product.id]: { ...views[result.product.id]!, expanded: true } }))
      void applyFocus({
        action: 'view_sellers', product_id: result.product.id,
        offer_ids: current.offers.slice(0, 24).map(offer => offer.id),
      })
      return
    }
    void fetchProductOffers(result, 1, false)
  }

  const loadMoreProductOffers = (result: CatalogSearchResult) => {
    const current = offerViews[result.product.id]
    if (!current || current.loading || current.offers.length >= current.total) return
    void fetchProductOffers(result, current.page + 1, true)
  }

  const contact = async (result: CatalogSearchResult | CatalogOffer) => {
    if (!missionId || contactingOfferId || contactInFlightRef.current || isRunning) return
    const offer = 'best_offer' in result ? result.best_offer : result
    contactInFlightRef.current = true
    setContactingOfferId(offer.id)
    setError(null)
    const requestKey = `${missionId}:${offer.id}`
    const clientRequestId = pendingContactIdsRef.current.get(requestKey)
      ?? globalThis.crypto.randomUUID()
    pendingContactIdsRef.current.set(requestKey, clientRequestId)
    try {
      const response = await createContactAttempt(missionId, {
        shopId: offer.shop.id, offerId: offer.id, clientRequestId,
      })
      pendingContactIdsRef.current.delete(requestKey)
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
      contactInFlightRef.current = false
      setContactingOfferId(null)
    }
  }

  const handleGenUIAction = (action: GenUIAction) => {
    if (isRunning || isRestoring) return
    if (action.type === 'verify_offer') {
      // Only allow options returned for this session's prior contact attempts.
      const offer = resolveRecoveryOffer(contactByOffer, action.offerId, action.shopId)
      if (!offer) {
        setError('این گزینه دیگر در پیشنهادهای معتبر مأموریت وجود ندارد. نتایج را دوباره بررسی کن.')
        return
      }
      void contact(offer)
      return
    }
    if (action.type === 'fill_query') {
      setMessage(action.query || lastQuery)
      composerInputRef.current?.focus()
      return
    }
    if (action.type === 'open_filter_form') {
      setActiveFilterForm({
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
            { id: 'brand_name', label: 'برند دقیق ثبت‌شده (اختیاری)', type: 'text', required: false, default_value: brandFilter ?? '', helper_text: 'اگر مشخص شود، تنها برند دقیق ثبت‌شده در دیتاست پذیرفته می‌شود.' },
            { id: 'model_exact', label: 'مدل دقیق ثبت‌شده (اختیاری)', type: 'text', required: false, default_value: modelFilter ?? '', helper_text: 'در صورت نامشخص‌بودن مدل در دیتاست، نتایج ممکن است صفر شوند.' },
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
      })
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
      const brandValue = typeof values.brand_name === 'string' ? values.brand_name.trim().slice(0, 300) : brandFilter
      const modelValue = typeof values.model_exact === 'string' ? values.model_exact.trim().slice(0, 500) : modelFilter
      const nextConstraints: MissionConstraints = {
        ...constraints,
        brand_name: brandValue || null,
        model_exact: modelValue || null,
        ...(hasBudgetField ? { max_price_toman: normalizedBudget || null } : {}),
        must_have_in_person_credit: credit,
        ...(location ? { lat: location.lat, lon: location.lon, radius_m: nextRadius } : {}),
        ...(Object.prototype.hasOwnProperty.call(values, 'sort') ? { sort: allowedSort } : {}),
      }
      if (!query) {
        setError('نام محصول را وارد کن تا بتوانم گزینه‌ها را پیدا کنم.')
        return
      }
      setBrandFilter(brandValue || null)
      setModelFilter(modelValue || null)
      onRestoreConstraints(nextConstraints, query)
      setActiveFilterForm(null)
      void runTurn(query, nextConstraints, query)
    }
  }

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    await runTurn(message, constraints)
  }

  const startNewMission = () => {
    offerRequestControllers.current.forEach((controller) => controller.abort())
    offerRequestControllers.current.clear()
    setOfferViews({})
    setMissionId(null)
    missionIdRef.current = null
    latestEventSeqRef.current = 0
    resultSetIdRef.current = null
    setResultSetId(null)
    setResultsStale(false)
    setSelectedOfferId(null)
    serverConstraintsRef.current = null
    storeMissionId(null)
    queuedTurnsRef.current = []
    setQueuedCount(0)
    queuePausedRef.current = false
    setQueuePaused(false)
    setMessage('')
    setEvents([])
    setChatMessages([])
    setLastQuery('')
    setSelectedCompareProductIds([])
    setSelectedProductId(null)
    setBrandFilter(null)
    setModelFilter(null)
    setComparisonOpen(false)
    setContactByOffer({})
    pendingContactIdsRef.current.clear()
    setActiveFilterForm(null)
    shouldAutoScrollRef.current = true
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
      credit: offer.in_person_credit_eligible ? 'برای این آفر ثبت‌شده' : 'برای این آفر ثبت نشده',
      updated,
      distance: formatDistance(offer.shop.distance_m) ?? 'محاسبه نشده',
      ...specComparison.valuesByProduct[index],
    }
  })
  const comparisonComponents: GenUIComponent[] = selectedCompareResults.length >= 2
    ? [{ type: 'comparison_table', id: 'live-selected-product-comparison', data: {
      title: 'مقایسه مدل‌های منتخب',
      columns: comparisonColumns,
      rows: comparisonRows,
    } }]
    : []

  const quickPrompts = [
    { label: 'لپ‌تاپ برای کار', detail: 'بودجه و مشخصات مهم را مقایسه کن', icon: <Laptop size={18} />, prompt: 'برای برنامه‌نویسی یک لپ‌تاپ مناسب در تهران پیدا کن؛ گزینه‌ها را با قیمت و مزایا مقایسه کن.' },
    { label: 'هدفون اقتصادی', detail: 'فروشگاه‌های ارزان‌تر را پیدا کن', icon: <Headphones size={18} />, prompt: 'هدفون بی‌سیم اقتصادی در تهران پیدا کن و ارزان‌ترین فروشگاه‌ها را مقایسه کن.' },
    { label: 'خرید اعتباری', detail: 'فقط پیشنهادهای دارای شرط اعتبار ثبت‌شده', icon: <CreditCard size={18} />, prompt: 'یک هدفون بی‌سیم در تهران می‌خواهم؛ فقط گزینه‌های فروشگاه‌هایی را نشان بده که خرید اعتباری حضوری می‌پذیرند.' },
  ]
  const isEmptyConversation = chatMessages.length === 0 && !isRestoring

  return (
    <section className={`conversation-panel${isEmptyConversation ? ' conversation-panel-empty' : ''}`} aria-labelledby="conversation-heading">
      <div className="conversation-panel-header">
        <div className="conversation-header-copy">
          <h2 id={!isEmptyConversation ? 'conversation-heading' : undefined}>دستیار خرید حضوری</h2>
        </div>
        {chatMessages.length > 0 && <button className="conversation-reset" type="button" disabled={isRunning || isRestoring || contactingOfferId !== null} onClick={startNewMission}><RotateCcw size={15} /> گفتگوی تازه</button>}
      </div>

      <div className="conversation-transcript" ref={transcriptRef} onScroll={(event) => {
        const transcript = event.currentTarget
        shouldAutoScrollRef.current = shouldFollowConversation(transcript.scrollHeight, transcript.scrollTop, transcript.clientHeight)
      }} aria-label="گفتگوی مأموریت خرید" aria-live="off" aria-busy={isRunning || isRestoring}>
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
          const isCurrentResult = currentResultsMessage?.id === item.id
          const preComponents = item.components.filter((component) => PRE_RESULT_COMPONENTS.has(component.type))
          // Local courtesy/help turns must not disable the last usable search form.
          // Older failed searches, however, should not fill the transcript with dead forms.
          const isActionableSearch = isCurrent || isCurrentResult
          const visiblePreComponents = isActionableSearch
            ? preComponents
            : preComponents.filter((component) => component.type === 'notice')
          const postComponents = item.components.filter((component) => !PRE_RESULT_COMPONENTS.has(component.type))
          const hasDedicatedEmptyState = item.components.some((component) => ['empty_state', 'clarification_form'].includes(component.type))
          return (
            <article className={`chat-message chat-message-assistant ${item.pending ? 'pending' : ''}`} key={item.id}>
              <div className="assistant-message-heading"><span className="assistant-mini-avatar"><Sparkles size={15} /></span><strong>دستیار خرید</strong>{item.pending && <span className="assistant-working"><i /><i /><i /> در حال بررسی</span>}</div>
              {item.text && !item.components.some((component) => component.type === 'empty_state') && (item.results && item.results.length > 0 && !item.pending
                ? <details className="assistant-explanation"><summary>درباره این نتایج <ChevronDown size={13} aria-hidden="true" /></summary><p>{item.text}</p></details>
                : <div className="assistant-message-copy">{item.text}</div>)}
              {!isActionableSearch && hasDedicatedEmptyState && (
                <p className="assistant-message-copy">این جست‌وجوی قبلی نتیجه‌ای نداشت؛ شرایط جست‌وجوی فعلی را از آخرین پیام اصلاح کن.</p>
              )}
              {visiblePreComponents.length > 0 && <GenUIRenderer components={visiblePreComponents} defaults={{ query: lastQuery, max_price_toman: budget, must_have_in_person_credit: mustHaveCredit, sort: constraints.sort ?? 'relevance' }} disabled={isRunning || isRestoring || !isActionableSearch} onAction={handleGenUIAction} />}
              {item.results && item.results.length > 0 && (
                <div className="mission-results-block conversation-results-block">
                  <div className="mission-results-header">
                    <div><h3>مدل‌هایی که می‌توانی بررسی کنی</h3>{isCurrentResult && <p className="mission-results-guidance">مدل را مقایسه کن یا فروشگاه‌هایش را ببین.</p>}</div>
                    <div className="mission-results-header-actions">
                      <span>{money.format(item.resultCount ?? item.results.length)} محصول</span>
                      {isCurrentResult && <button type="button" className="mission-edit-filters" onClick={() => handleGenUIAction({ type: 'open_filter_form' })} disabled={isRunning || isRestoring}><SlidersHorizontal size={15} /> تغییر شرایط</button>}
                    </div>
                  </div>
                  {isCurrentResult && resultsStale && <div className="mission-stale-warning" role="status">
                    شرایط مأموریت تغییر کرده است. کارت‌های قبلی فقط برای مراجعه تاریخی هستند و انتخاب یا استعلام از آن‌ها غیرفعال است.
                    <button type="button" disabled={isRunning || isRestoring || !lastQuery}
                      onClick={() => void runTurn(lastQuery, serverConstraintsRef.current ?? constraints, lastQuery)}>به‌روزرسانی نتایج</button>
                  </div>}
                  {isCurrentResult && <ActiveShoppingFilters constraints={constraints} disabled={isRunning || isRestoring}
                    onEdit={() => handleGenUIAction({type:'open_filter_form'})} />}
                  {isCurrentResult && selectedCompareResults.length > 0 && (
                    <div className="mission-compare-tray" role="region" aria-label="انتخاب‌های مقایسه">
                      <div className="mission-compare-tray-copy">
                        <strong>{money.format(selectedCompareResults.length)} مدل برای مقایسه</strong>
                        <span>{selectedCompareResults.length === 1 ? 'یک مدل دیگر انتخاب کن.' : 'تفاوت قیمت و مشخصات را ببین.'}</span>
                      </div>
                      <div className="mission-compare-tray-actions">
                        {selectedCompareResults.length >= 2 && <button type="button" className="mission-compare-toggle"
                          aria-expanded={comparisonOpen} onClick={() => setComparisonOpen((open) => !open)}>
                          {comparisonOpen ? 'بستن مقایسه' : 'نمایش مقایسه'}
                        </button>}
                        <button type="button" className="mission-compare-clear" aria-label="پاک کردن انتخاب‌های مقایسه"
                          onClick={() => { setSelectedCompareProductIds([]); setComparisonOpen(false) }}>
                          پاک کردن
                        </button>
                      </div>
                    </div>
                  )}
                  {isCurrentResult && !resultsStale && comparisonOpen && comparisonComponents.length > 0 && <GenUIRenderer components={comparisonComponents} defaults={{ query: lastQuery, max_price_toman: budget, must_have_in_person_credit: mustHaveCredit, sort: constraints.sort ?? 'relevance' }} disabled={isRunning || isRestoring} onAction={handleGenUIAction} />}
                  <ProductResults
                    results={item.results}
                    missionId={missionId ?? ''}
                    onContact={contact}
                    contactingOfferId={contactingOfferId}
                    contactByOffer={contactByOffer}
                    selectedCompareProductIds={isCurrentResult ? selectedCompareProductIds : []}
                    onToggleCompare={toggleComparedProduct}
                    selectedProductId={isCurrentResult ? selectedProductId : null}
                    selectedOfferId={isCurrentResult ? selectedOfferId : null}
                    onSelectProduct={(id) => { void applyFocus({ action: 'select_product', product_id: id }) }}
                    onSelectOffer={(id) => { void applyFocus({ action: 'select_offer', offer_id: id }) }}
                    offerViews={offerViews}
                    onToggleOffers={toggleProductOffers}
                    onLoadMoreOffers={loadMoreProductOffers}
                    allowActions={isCurrentResult && !resultsStale && !isRunning && !isRestoring}
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
      </div>

      <dialog ref={filterDialogRef} className="mission-filter-dialog" onClose={() => setActiveFilterForm(null)} aria-labelledby="filter-dialog-title">
        <div className="mission-filter-dialog-head">
          <h2 id="filter-dialog-title">تغییر شرایط خرید</h2>
          <button type="button" aria-label="بستن تنظیمات" onClick={() => setActiveFilterForm(null)}><X size={20} /></button>
        </div>
        {activeFilterForm && <GenUIRenderer key={activeFilterForm.id} components={[activeFilterForm]} defaults={{ query: lastQuery, max_price_toman: budget, must_have_in_person_credit: mustHaveCredit, sort: constraints.sort ?? 'relevance' }} disabled={isRunning || isRestoring} onAction={handleGenUIAction} />}
      </dialog>

      {error && <div className="conversation-error" role="alert">
        <AlertCircle size={17} /><span>{error}</span>
        {missionId && <button type="button" disabled={isRunning || isRestoring}
          onClick={() => void restoreLatestMission()}>بازیابی وضعیت</button>}
        <button type="button" onClick={() => setError(null)}>بستن</button>
      </div>}
      {isRunning && <div className="conversation-running-note" role="status" aria-live="polite"><span className="mission-progress-dot" />{stageLabel ?? 'در حال بررسی درخواست'}<span className="conversation-running-sub">اطلاعات محصول و شروط خرید در حال بررسی است</span></div>}
      {queuedCount > 0 && <div className="conversation-queue" aria-label="پیام‌های در انتظار">
        <p role="status">{queuePaused
          ? 'ارسال پیام‌های بعدی متوقف شد. ابتدا وضعیت درخواست قبلی را بازیابی کن.'
          : `${money.format(queuedCount)} پیام در صف پردازش است.`}</p>
        <ol>{queuedTurnsRef.current.map((item, index) => <li key={index}>
          <span>{item.text}</span>
          <button type="button" onClick={() => removeQueuedTurn(index, true)}>ویرایش</button>
          <button type="button" onClick={() => removeQueuedTurn(index, false)}>حذف</button>
        </li>)}</ol>
        {queuePaused && <button type="button" disabled={isRunning || isRestoring || Boolean(error)}
          onClick={resumeQueue}>ادامه صف پس از بررسی وضعیت</button>}
      </div>}

      <form className="conversation-composer" id="conversation-composer" onSubmit={submit}>
        {lastQuery && <button className="composer-tool" type="button" aria-label="تنظیم شرایط خرید" title="تنظیم شرایط خرید" disabled={isRunning || isRestoring} onClick={() => handleGenUIAction({ type: 'open_filter_form' })}><SlidersHorizontal size={18} /></button>}
        <button className={`composer-tool ${location ? 'location-active' : ''}`} type="button" aria-label={location ? 'حذف موقعیت' : 'استفاده از موقعیت فعلی'} title={location ? 'حذف فیلتر موقعیت' : 'مرتب‌سازی فروشگاه‌ها بر اساس فاصله از موقعیت فعلی'} disabled={isRunning || isRestoring || isLocating} onClick={handleLocationClick}>{isLocating ? <LoaderCircle size={18} className="spin" /> : location ? <MapPinOff size={18} /> : <LocateFixed size={18} />}</button>
        <textarea
          ref={composerInputRef}
          aria-label="پیام به دستیار خرید"
          rows={1}
          maxLength={2000}
          value={message}
          disabled={isRestoring}
          onChange={(event) => setMessage(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault()
              event.currentTarget.form?.requestSubmit()
            }
          }}
          placeholder="مثلاً تا ۳ میلیون تومان یک هدفون مناسب برای رفت‌وآمد پیدا کن…"
        />
        <button className="composer-send" type="submit" aria-label="ارسال پیام" title="ارسال پیام" disabled={!message.trim() || isRestoring}>
          <Send size={17} />
        </button>
      </form>
      
      <div className="conversation-bottom-row">
        <div className="mission-context-row">
          {formatBudgetLabel(budget) && <span>بودجه: {formatBudgetLabel(budget)}</span>}
          {mustHaveCredit && <span>خرید اعتباری حضوری</span>}
          {location && <span><MapPin size={13} /> فاصله مستقیم تا {money.format(radiusM / 1000)} کیلومتر</span>}
          {isLocating && <span><LoaderCircle size={13} className="spin" /> دریافت موقعیت…</span>}
        </div>
        <button className="mission-manual-region-toggle" type="button" aria-expanded={showRegionPicker} disabled={isRunning || isRestoring} onClick={() => setShowRegionPicker(value => !value)}>
          <MapPin size={13} /> انتخاب دستی محدوده
        </button>
        <details className="conversation-disclosure">
          <summary>درباره داده‌ها</summary>
          <p>قیمت‌ها تاریخی‌اند و موجودی به‌صورت نمایشی بررسی می‌شود. بیشتر نام فروشگاه‌ها و همه شماره‌های تماس دیتاست مسابقه ساختگی‌اند.</p>
        </details>
      </div>
      {showRegionPicker && (
        <div className="mission-manual-region-panel">
          <label htmlFor="manual-tehran-region">محدوده تقریبی اطراف فروشگاه‌های دیتاست</label>
          <select id="manual-tehran-region" value={selectedRegionId} disabled={isRunning || isRestoring} onChange={event => applyManualRegion(event.target.value)}>
            <option value="">یک محدوده انتخاب کن</option>
            {TEHRAN_REGION_SAMPLES.map(area => <option key={area.id} value={area.id}>{area.label}</option>)}
          </select>
          <small>این مختصات نمونه‌اند؛ همه فروشگاه‌های تهران در دیتاست حضور ندارند.</small>
        </div>
      )}
    </section>
  )
}
