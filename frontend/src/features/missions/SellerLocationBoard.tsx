import { useState } from 'react'
import { ExternalLink, LocateFixed, MapPin, Store } from 'lucide-react'
import type { CatalogOffer } from '../search/catalog-api'
import { isTehranCatalogPoint, neshanDrivingUrl, neshanPointUrl, osmEmbedUrl } from './shop-map'
import { formatDistance, openStreetMapUrl } from './ui-formatters'
import { currentRouteEvidence, routeEvidenceScope } from './routing-evidence'
import {
  getRoutingCapability, requestRouteEstimates,
  type RouteEstimateResponse, type RoutingCapability,
} from './mission-api'

const numerals = new Intl.NumberFormat('fa-IR', { maximumFractionDigits: 0 })

// An intentional opt-in: a missing value means there are no paid Neshan controls,
// no provider-capability requests, and no user-facing upsell.
export const paidNeshanRoutingUiEnabled = import.meta.env.VITE_ENABLE_PAID_NESHAN_ROUTES === '1'

/** An offer must carry its own valid shop coordinates. Never geocode a synthetic name. */
export function geographicallyMappedOffers(offers: CatalogOffer[]): CatalogOffer[] {
  return offers.filter(({ shop }) => isTehranCatalogPoint(shop.lat, shop.lon)
    && osmEmbedUrl(shop.lat, shop.lon) !== null)
}

export function selectedMappedOffer(
  offers: CatalogOffer[],
  selectedOfferId: string | null,
): CatalogOffer | null {
  if (!selectedOfferId) return null
  return geographicallyMappedOffers(offers).find((offer) => offer.id === selectedOfferId) ?? null
}

type Props = {
  offers: CatalogOffer[]
  selectedOfferId: string | null
  onSelectOffer: (offerId: string) => void
  disabled: boolean
  missionId: string
  resultSetId: string | null
  origin?: { lat: number; lon: number } | null
}

/** A shared *real location preview*, not a fake street map or a routing engine.
 * Opening the third-party embed is explicitly user-triggered.
 */
export function SellerLocationBoard({
  offers, selectedOfferId, onSelectOffer, disabled, missionId, resultSetId, origin,
}: Props) {
  const [openMapOfferId, setOpenMapOfferId] = useState<string | null>(null)
  const [routingCapability, setRoutingCapability] = useState<{missionId: string; data: RoutingCapability} | null>(null)
  const [routingCheckedMission, setRoutingCheckedMission] = useState<string | null>(null)
  const [capabilityError, setCapabilityError] = useState<{missionId: string; text: string} | null>(null)
  const [routeMode, setRouteMode] = useState<'car' | 'motorcycle'>('car')
  const [routeBusy, setRouteBusy] = useState(false)
  const [directionBusy, setDirectionBusy] = useState(false)
  const [directionResult, setDirectionResult] = useState<{scope: string; data: RouteEstimateResponse} | null>(null)
  const [routeResult, setRouteResult] = useState<{scope: string; data: RouteEstimateResponse} | null>(null)
  const [routeError, setRouteError] = useState<{scope: string; message: string} | null>(null)
  const mapped = geographicallyMappedOffers(offers)
  const distinctMappedShopCount = new Set(mapped.map(offer => offer.shop.id)).size
  const currentOffer = offers.find(offer => offer.id === selectedOfferId)
  const active = selectedMappedOffer(offers, selectedOfferId)
  const iframeUrl = active ? osmEmbedUrl(active.shop.lat, active.shop.lon) : null
  const externalUrl = active ? openStreetMapUrl(active.shop.lat, active.shop.lon) : null
  const neshanPoint = active ? neshanPointUrl(active.shop.lat, active.shop.lon) : null
  const neshanDrive = active ? neshanDrivingUrl(origin, {lat: active.shop.lat, lon: active.shop.lon}) : null

  const mapVisible = Boolean(active && openMapOfferId === active.id)
  const uniqueDestinations = mapped.filter((offer, index, all) =>
    all.findIndex((candidate) => candidate.shop.id === offer.shop.id) === index
  ).slice(0, 5)
  const routingChecked = routingCheckedMission === missionId
  const activeCapability = routingCapability?.missionId === missionId ? routingCapability.data : null
  const visibleCapabilityError = capabilityError?.missionId === missionId ? capabilityError.text : null
  // A late answer for an old mission, result set, origin, mode or seller list
  // is kept out of sight, even if the provider response arrives successfully.
  const routeScope = routeEvidenceScope({
    missionId, resultSetId, origin, mode: routeMode, destinations: uniqueDestinations,
  })
  const visibleRouteResult = currentRouteEvidence(routeResult, routeScope, disabled)?.data ?? null
  const visibleRouteError = currentRouteEvidence(routeError, routeScope, disabled)?.message ?? null
  const directionScope = routeScope + ':' + (selectedOfferId ?? '')
  const visibleDirection = currentRouteEvidence(directionResult, directionScope, disabled)?.data ?? null

  const checkRouting = (opened: boolean, force = false) => {
    if (!paidNeshanRoutingUiEnabled || !opened || disabled || !resultSetId
      || (!force && routingChecked) || !missionId) return
    setRoutingCheckedMission(missionId)
    setCapabilityError(null)
    void getRoutingCapability(missionId)
      .then(data => setRoutingCapability({missionId, data}))
      .catch(() => setCapabilityError({missionId,
        text: 'وضعیت سرویس مسیریابی در دسترس نیست؛ فهرست و مکان ثبت‌شده برقرار است.'}))
  }

  const calculateRoutes = async () => {
    if (!activeCapability?.enabled || !origin || !resultSetId || routeBusy || disabled
      || uniqueDestinations.length === 0) return
    setRouteBusy(true)
    setRouteError(null)
    setRouteResult(null)
    try {
      const result = await requestRouteEstimates(missionId, {
        result_set_id: resultSetId,
        origin: { ...origin, source: 'manual_region' },
        offer_ids: uniqueDestinations.map((offer) => offer.id),
        mode: routeMode,
      })
      setRouteResult({scope: routeScope, data: result})
    } catch (error) {
      setRouteError({scope: routeScope,
        message: error instanceof Error ? error.message : 'دریافت زمان سفر ممکن نشد.'})
    } finally {
      setRouteBusy(false)
    }
  }

  const calculateOneRoute = async () => {
    if (!activeCapability?.direction_enabled || !origin || !resultSetId
      || !active || disabled || directionBusy || routeBusy) return
    setDirectionBusy(true)
    setDirectionResult(null)
    const requestedScope = directionScope
    try {
      const data = await requestRouteEstimates(missionId, {
        result_set_id: resultSetId,
        origin: { ...origin, source: 'manual_region' },
        offer_ids: [active.id], mode: routeMode, service: 'direction',
      })
      setDirectionResult({scope: requestedScope, data})
    } catch {
      setDirectionResult({scope: requestedScope, data: {
        provider: 'neshan', mode: routeMode, status: 'unavailable',
        estimates: [], availability_verified: false,
        source: 'provider_route_estimate',
      }})
    } finally {
      setDirectionBusy(false)
    }
  }

  if (offers.length === 0) return null
  return (
    <details className="mission-seller-location-board" onToggle={(event) => checkRouting(event.currentTarget.open)}>
      <summary><MapPin size={16} aria-hidden="true" />
        {offers.length > 1 ? 'مقایسهٔ مکان فروشگاه‌ها' : 'موقعیت فروشنده'}
        <span className="mission-location-count">{numerals.format(distinctMappedShopCount)} فروشگاه دارای مختصات ثبت‌شده از {numerals.format(offers.length)} آفرِ بارگذاری‌شده</span>
      </summary>
      <div className="mission-location-content">
        <p className="mission-location-disclaimer">
          این فهرست فقط آفرهای ثبت‌شده برای همین مدل را نشان می‌دهد، نه موجودی تأییدشده.
          نام بسیاری از فروشگاه‌های دیتاست آزمایشی ساختگی است. مختصات، مکان ثبت‌شده‌اند؛
          فاصله‌ها مستقیم هستند و زمان سفر یا مسیر داخل پاساژ مشخص نیست.
        </p>
        {disabled && <p role="note">فهرست در حال بارگذاری یا متعلق به نتیجهٔ غیرفعال است؛ تا دریافت نتیجهٔ معتبر انتخاب و نمایش نقشه غیرفعال‌اند.</p>}
        <div className="mission-location-choices" role="group" aria-label="انتخاب فروشنده برای دیدن موقعیت">
          {offers.map((offer, index) => {
            const isSelected = offer.id === selectedOfferId
            const distance = formatDistance(offer.shop.distance_m)
            return (
              <button type="button" key={offer.id} onClick={() => { setOpenMapOfferId(null); onSelectOffer(offer.id) }}
                className="mission-location-choice" disabled={disabled}
                aria-pressed={isSelected}>
                <span className="mission-location-choice-title">
                  <Store size={14} aria-hidden="true" />
                  {numerals.format(index + 1)}. {offer.shop.name || 'فروشگاه بدون نام'}
                </span>
                <small>{distance ? `فاصله مستقیم: ${distance}` : 'فاصله از مبدأ مشخص نشده'}
                  {isTehranCatalogPoint(offer.shop.lat, offer.shop.lon) ? '' : ' · مختصات معتبر تهران ثبت نشده'}
                </small>
              </button>
            )
          })}
        </div>
        <div className="mission-location-preview" role="region" aria-label="موقعیت فروشندهٔ منتخب">
          {!selectedOfferId
            ? <p>برای مشاهدهٔ موقعیت، ابتدا یکی از فروشنده‌های همین مدل را انتخاب کن.</p>
            : !currentOffer
              ? <p>فروشندهٔ انتخابی متعلق به فهرست دیگری است؛ از همین فهرست انتخاب کن.</p>
            : !active || !iframeUrl
              ? <p>برای این فروشنده مختصات معتبر در محدودهٔ پوشش تهران ثبت نشده است. نشانی نوشته‌شده را بررسی کن.</p>
              : <>
                  <strong><MapPin size={15} aria-hidden="true" /> مکان ثبت‌شده: {active.shop.name}</strong>
                  <p>{active.shop.address || active.shop.location_label || 'نشانی دقیق ثبت نشده'}</p>
                  {!mapVisible
                    ? <button type="button" className="mission-location-load-map"
                        onClick={() => setOpenMapOfferId(selectedOfferId)} disabled={disabled}>
                        نمایش نقشه OpenStreetMap
                      </button>
                    : <div className="mission-location-map">
                        <iframe src={iframeUrl} loading="lazy" referrerPolicy="no-referrer"
                          title={`موقعیت ثبت‌شده ${active.shop.name}، بدون مسیر و زمان سفر`} />
                        <button type="button" onClick={() => setOpenMapOfferId(null)}>بستن نقشه</button>
                      </div>}
                  <small>با نمایش نقشه، مختصات این فروشنده برای OpenStreetMap ارسال می‌شود؛ نام فروشگاه یا موجودی تأیید نمی‌شود.</small>
                  {neshanPoint && !disabled && <a href={neshanPoint} target="_blank" rel="noopener noreferrer"
                    aria-label="بازکردن مختصات ثبت‌شده در نقشه نشان، نه تأیید فروشگاه">
                    <ExternalLink size={13} aria-hidden="true" />
                    بازکردن نقطه ثبت‌شده در نشان
                  </a>}
                  {neshanDrive && !disabled && <a href={neshanDrive} target="_blank" rel="noopener noreferrer"
                    aria-label="بازکردن مسیر خودرو از مبدأ انتخابی تا مختصات ثبت‌شده در نشان">
                    <ExternalLink size={13} aria-hidden="true" />
                    مسیر خودرو در نشان تا مختصات ثبت‌شده
                  </a>}
                  {!origin && <small>برای لینک مسیریابی از محدوده انتخابی، ابتدا مبدأ تهران را در فیلترها تعیین کن.</small>}
                  {(neshanPoint || neshanDrive) && <small>
                    با بازکردن این لینک، مختصات مربوطه به نشان ارسال می‌شود. ممکن است نشان مسیر را در سایت یا اپ خودش نمایش دهد؛
                    این کار به معنی وجود فروشگاه در آن نقطه، بازبودن یا موجودی واقعی نیست. این لینک از سهمیه API مسیریابی پروژه استفاده نمی‌کند.
                  </small>}
                  {externalUrl && !disabled && <a href={externalUrl} target="_blank" rel="noopener noreferrer">
                    <ExternalLink size={13} aria-hidden="true" /> بازکردن نقطه در OpenStreetMap
                  </a>}
                </>
          }
        </div>
        {paidNeshanRoutingUiEnabled && <section className="mission-neshan-routing" aria-label="مقایسه زمان سفر با نشان">
          <strong>مقایسه زمان سفر با نشان (اختیاری)</strong>
          <p>این بخش فقط در صورت فعال‌بودن سرویس، بعد از انتخاب مبدأ و درخواست مستقیم تو محاسبه می‌شود.
            زمان‌های نشان تخمینی‌اند؛ نام فروشگاه‌ها و موجودی آن‌ها تأیید نشده‌اند.</p>
          {!routingChecked && <small>وضعیت سرویس پس از بازکردن این بخش بررسی می‌شود.</small>}
          {routingChecked && !activeCapability && !visibleCapabilityError && <small>در حال بررسی قابلیت مسیریابی…</small>}
          {visibleCapabilityError && <div role="status">
            <p>{visibleCapabilityError}</p>
            <button type="button" disabled={disabled}
              onClick={() => checkRouting(true, true)}>تلاش دوباره برای بررسی سرویس</button>
          </div>}
          {activeCapability && !activeCapability.enabled && <p role="status">
            اتصال مسیریابی نشان هنوز فعال نشده است. فهرست و نشانی‌های ثبت‌شده همچنان قابل استفاده‌اند.
          </p>}
          {!origin && <p>ابتدا از تنظیمات جست‌وجو، منطقه مبدأ تهران را مشخص کن.</p>}
          {activeCapability?.enabled && origin && <div className="mission-route-actions">
            <label>نوع سفر
              <select value={routeMode} disabled={disabled || routeBusy}
                onChange={(event) => { setRouteMode(event.target.value as 'car' | 'motorcycle'); setRouteResult(null); setDirectionResult(null) }}>
                <option value="car">خودرو</option>
                <option value="motorcycle">موتورسیکلت</option>
              </select>
            </label>
            <button type="button" disabled={disabled || routeBusy || !resultSetId || uniqueDestinations.length === 0}
              onClick={() => { void calculateRoutes() }}>
              {routeBusy ? 'در حال دریافت از نشان…' : 'محاسبه زمان سفر (درخواست به نشان)'}
            </button>
          </div>}
          {activeCapability?.direction_enabled && origin && <div className="mission-route-actions">
            <button type="button"
              disabled={disabled || routeBusy || directionBusy || !active || !resultSetId}
              onClick={() => { void calculateOneRoute() }}>
              {directionBusy ? 'در حال دریافت مسیر…' : 'محاسبه مسیر فروشنده منتخب (درخواست جداگانه)'}
            </button>
            <small>این اقدام یک فراخوانی پولی مجزا دارد. قبل از حرکت، نام و نشانی فروشگاه را مستقل بررسی کن.</small>
          </div>}
          {visibleDirection?.status === 'unavailable' && <p role="status">
            مسیر این فروشنده از نشان دریافت نشد؛ مدت سفر اعلام نمی‌شود.
          </p>}
          {visibleDirection?.status === 'ok' && visibleDirection.route?.offer_id === selectedOfferId &&
            <div className="mission-route-results" role="status">
              <strong>مسیر پیشنهادی نشان برای فروشنده انتخاب‌شده</strong>
              <p>{numerals.format(Math.ceil(visibleDirection.route.duration_seconds / 60))} دقیقه،
                {numerals.format(visibleDirection.route.route_distance_meters)} متر مسیر با {routeMode === 'car' ? 'خودرو' : 'موتورسیکلت'}</p>
              <small>این زمان تخمینی است، نه زمان رسیدن قطعی یا تأیید هویت و موجودی فروشگاه. نمایش خطوط مسیر داخل نقشه پس از فعال‌سازی کلید Web SDK امکان‌پذیر خواهد شد.</small>
            </div>}
          {visibleRouteError && <p role="status">{visibleRouteError} هیچ زمان فرضی نمایش داده نمی‌شود.</p>}
          {visibleRouteResult?.status === 'unavailable' && <p role="status">
            مسیریابی در حال حاضر در دسترس نیست؛ زمان سفر قابل اعتماد نداریم.
          </p>}
          {visibleRouteResult?.status === 'ok' && <div className="mission-route-results">
            <small>زمان تخمینی با ترافیک از نشان، در لحظه درخواست. ممکن است تغییر کند و تأیید موجودی نیست.</small>
            <ul>{visibleRouteResult.estimates.map((estimate) => {
              const offer = offers.find((row) => row.id === estimate.offer_id)
              if (!offer) return null
              const duration = estimate.status === 'ok' && typeof estimate.duration_seconds === 'number'
                ? `${numerals.format(Math.max(1, Math.ceil(estimate.duration_seconds / 60)))} دقیقه` : null
              const distance = estimate.status === 'ok' && typeof estimate.route_distance_meters === 'number'
                ? `${numerals.format(estimate.route_distance_meters)} متر مسیر` : null
              return <li key={estimate.offer_id}>
                <span>{offer.shop.name}</span>
                <strong>{duration ?? (estimate.status === 'no_route' ? 'مسیر پیدا نشد' : 'نامشخص')}</strong>
                {distance && <small>{distance}</small>}
              </li>
            })}</ul>
          </div>}
        </section>}
        <p className="mission-location-footer"><LocateFixed size={14} aria-hidden="true" />
          موقعیت نمایش‌داده‌شده فقط مختصات ثبت‌شده است؛ فاصله مستقیم، زمان سفر نیست.
          این نقشه موجودی یا هویت فروشگاه را تأیید نمی‌کند.
        </p>
      </div>
    </details>
  )
}
