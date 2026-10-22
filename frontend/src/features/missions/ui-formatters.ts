const persianInteger = new Intl.NumberFormat('fa-IR', { maximumFractionDigits: 0 })
const persianDistance = new Intl.NumberFormat('fa-IR', { maximumFractionDigits: 1 })
const DAY_MS = 24 * 60 * 60 * 1000

type PriceQuality = 'recent_change' | 'stale' | 'unknown_timestamp' | 'unknown_price'

export function getPriceQualityLabel(quality: PriceQuality | string | null | undefined): string {
  switch (quality) {
    case 'recent_change':
      return 'تغییر قیمت اخیر'
    case 'stale':
      return 'قدیمی‌تر از ۷ روز'
    case 'unknown_price':
      return 'قیمت ثبت نشده'
    case 'unknown_timestamp':
    default:
      return 'زمان قیمت نامشخص'
  }
}

/** Render the stored price-change timestamp without implying live inventory. */
export function formatLastPriceChange(value: string | null | undefined, now = Date.now()): string {
  if (!value) return 'زمان تغییر قیمت ثبت نشده'
  const timestamp = Date.parse(value)
  if (!Number.isFinite(timestamp) || timestamp > now + 5 * 60 * 1000) return 'زمان تغییر قیمت نامشخص'

  const ageInDays = Math.floor(Math.max(0, now - timestamp) / DAY_MS)
  if (ageInDays === 0) return 'آخرین تغییر: امروز'
  if (ageInDays === 1) return 'آخرین تغییر: دیروز'
  if (ageInDays < 7) return `آخرین تغییر: ${persianInteger.format(ageInDays)} روز پیش`

  try {
    const date = new Date(timestamp)
    const formatted = new Intl.DateTimeFormat('fa-IR', {
      dateStyle: 'medium',
      timeZone: 'Asia/Tehran',
    }).format(date)
    return `آخرین تغییر: ${formatted}`
  } catch {
    return 'زمان تغییر قیمت نامشخص'
  }
}

export function formatDistance(distanceM: number | null | undefined): string | null {
  if (typeof distanceM !== 'number' || !Number.isFinite(distanceM) || distanceM < 0) return null
  if (distanceM < 1000) return `${persianInteger.format(Math.round(distanceM))} متر`
  return `${persianDistance.format(distanceM / 1000)} کیلومتر`
}

/** Only numeric catalogue coordinates are permitted in the external map URL. */
export function openStreetMapUrl(lat: number | null | undefined, lon: number | null | undefined): string | null {
  if (typeof lat !== 'number' || typeof lon !== 'number' || !Number.isFinite(lat) || !Number.isFinite(lon)) return null
  if (lat < -90 || lat > 90 || lon < -180 || lon > 180) return null
  return `https://www.openstreetmap.org/?mlat=${lat}&mlon=${lon}#map=17/${lat}/${lon}`
}
