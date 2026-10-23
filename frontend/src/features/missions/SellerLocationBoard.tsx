import { useState } from 'react'
import { ExternalLink, LocateFixed, MapPin, Store } from 'lucide-react'
import type { CatalogOffer } from '../search/catalog-api'
import { osmEmbedUrl } from './shop-map'
import { formatDistance, openStreetMapUrl } from './ui-formatters'

const numerals = new Intl.NumberFormat('fa-IR', { maximumFractionDigits: 0 })

/** An offer must carry its own valid shop coordinates. Never geocode a synthetic name. */
export function geographicallyMappedOffers(offers: CatalogOffer[]): CatalogOffer[] {
  return offers.filter(({ shop }) => osmEmbedUrl(shop.lat, shop.lon) !== null)
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
}

/** A shared *real location preview*, not a fake street map or a routing engine.
 * Opening the third-party embed is explicitly user-triggered.
 */
export function SellerLocationBoard({ offers, selectedOfferId, onSelectOffer, disabled }: Props) {
  const [openMapOfferId, setOpenMapOfferId] = useState<string | null>(null)
  const mapped = geographicallyMappedOffers(offers)
  const active = selectedMappedOffer(offers, selectedOfferId)
  const iframeUrl = active ? osmEmbedUrl(active.shop.lat, active.shop.lon) : null
  const externalUrl = active ? openStreetMapUrl(active.shop.lat, active.shop.lon) : null

  const mapVisible = Boolean(active && openMapOfferId === active.id)

  if (offers.length < 2) return null
  return (
    <details className="mission-seller-location-board">
      <summary><MapPin size={16} aria-hidden="true" /> مقایسهٔ مکان فروشگاه‌ها
        <span className="mission-location-count">{numerals.format(mapped.length)} موقعیت ثبت‌شده از {numerals.format(offers.length)} آفرِ بارگذاری‌شده</span>
      </summary>
      <div className="mission-location-content">
        <p className="mission-location-disclaimer">
          این فهرست فقط آفرهای ثبت‌شده برای همین مدل را نشان می‌دهد، نه موجودی تأییدشده.
          نام بسیاری از فروشگاه‌های دیتاست آزمایشی ساختگی است. مختصات، مکان ثبت‌شده‌اند؛
          فاصله‌ها مستقیم هستند و زمان سفر یا مسیر داخل پاساژ مشخص نیست.
        </p>
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
                  {osmEmbedUrl(offer.shop.lat, offer.shop.lon) ? '' : ' · مختصات نامشخص'}
                </small>
              </button>
            )
          })}
        </div>
        <div className="mission-location-preview" role="region" aria-label="موقعیت فروشندهٔ منتخب">
          {!selectedOfferId
            ? <p>برای مشاهدهٔ موقعیت، ابتدا یکی از فروشنده‌ها را انتخاب کن.</p>
            : !active || !iframeUrl
              ? <p>برای این فروشنده مختصات معتبر ثبت نشده است. نشانی نوشته‌شده را بررسی کن.</p>
              : <>
                  <strong><MapPin size={15} aria-hidden="true" /> مکان ثبت‌شده: {active.shop.name}</strong>
                  <p>{active.shop.address || active.shop.location_label || 'نشانی دقیق ثبت نشده'}</p>
                  {!mapVisible
                    ? <button type="button" className="mission-location-load-map"
                        onClick={() => setOpenMapOfferId(active.id)}>
                        نمایش نقشه OpenStreetMap
                      </button>
                    : <div className="mission-location-map">
                        <iframe src={iframeUrl} loading="lazy" referrerPolicy="no-referrer"
                          title={`موقعیت ثبت‌شده ${active.shop.name}، بدون مسیر و زمان سفر`} />
                        <button type="button" onClick={() => setOpenMapOfferId(null)}>بستن نقشه</button>
                      </div>}
                  <small>با نمایش نقشه، مختصات این فروشنده برای OpenStreetMap ارسال می‌شود؛ نام فروشگاه یا موجودی تأیید نمی‌شود.</small>
                  {externalUrl && <a href={externalUrl} target="_blank" rel="noopener noreferrer">
                    <ExternalLink size={13} aria-hidden="true" /> بازکردن نقطه در OpenStreetMap
                  </a>}
                </>
          }
        </div>
        <p className="mission-location-footer"><LocateFixed size={14} aria-hidden="true" />
          این نما فقط مکان فروشندهٔ انتخاب‌شده را روی نقشه نشان می‌دهد؛
          نقشهٔ هم‌زمان چندپین یا تخمین مسیر نیست.</p>
      </div>
    </details>
  )
}
