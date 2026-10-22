import { useQuery } from '@tanstack/react-query'
import { useCallback, useEffect, useState } from 'react'
import { MissionPanel } from '../features/missions/MissionPanel'
import type { MissionConstraints } from '../features/missions/mission-api'
import { getHealth } from '../shared/api/health'

const SEARCH_PREFERENCES_KEY = 'bazaar-compass:search-preferences'

type SavedLocation = { lat: number; lon: number }
type ShoppingSort = NonNullable<MissionConstraints['sort']>

type SearchPreferences = {
  maxPriceToman: string
  mustHaveCredit: boolean
  location: SavedLocation | null
  radiusM: number
  sort: ShoppingSort
}

function readSearchPreferences(): SearchPreferences {
  const fallback: SearchPreferences = { maxPriceToman: '', mustHaveCredit: false, location: null, radiusM: 3000, sort: 'relevance' }
  try {
    const stored = sessionStorage.getItem(SEARCH_PREFERENCES_KEY)
    if (!stored) return fallback
    const value = JSON.parse(stored) as Partial<SearchPreferences>
    return {
      maxPriceToman: typeof value.maxPriceToman === 'string' ? value.maxPriceToman : fallback.maxPriceToman,
      mustHaveCredit: typeof value.mustHaveCredit === 'boolean' ? value.mustHaveCredit : fallback.mustHaveCredit,
      location: value.location && typeof value.location === 'object'
        && typeof value.location.lat === 'number' && Number.isFinite(value.location.lat)
        && typeof value.location.lon === 'number' && Number.isFinite(value.location.lon)
        ? { lat: value.location.lat, lon: value.location.lon }
        : fallback.location,
      radiusM: typeof value.radiusM === 'number' && [1000, 3000, 5000, 10000].includes(value.radiusM) ? value.radiusM : fallback.radiusM,
      sort: ['relevance', 'price_asc', 'distance_asc', 'recent_price_change'].includes(String(value.sort))
        ? value.sort as ShoppingSort
        : fallback.sort,
    }
  } catch {
    return fallback
  }
}

export default function App() {
  const health = useQuery({ queryKey: ['health', 'ready'], queryFn: ({ signal }) => getHealth(signal), retry: 0 })
  const [initialPreferences] = useState(readSearchPreferences)
  const [maxPriceToman, setMaxPriceToman] = useState(initialPreferences.maxPriceToman)
  const [mustHaveCredit, setMustHaveCredit] = useState(initialPreferences.mustHaveCredit)
  const [location, setLocation] = useState<SavedLocation | null>(initialPreferences.location)
  const [radiusM, setRadiusM] = useState(initialPreferences.radiusM)
  const [sort, setSort] = useState<ShoppingSort>(initialPreferences.sort)

  useEffect(() => {
    try {
      const preferences: SearchPreferences = { maxPriceToman, mustHaveCredit, location, radiusM, sort }
      sessionStorage.setItem(SEARCH_PREFERENCES_KEY, JSON.stringify(preferences))
    } catch {
      // The conversation remains usable when browser storage is unavailable.
    }
  }, [maxPriceToman, mustHaveCredit, location, radiusM, sort])

  const restoreMissionFilters = useCallback((constraints: MissionConstraints) => {
    setMaxPriceToman(constraints.max_price_toman ?? '')
    setMustHaveCredit(Boolean(constraints.must_have_in_person_credit))
    setLocation(typeof constraints.lat === 'number' && typeof constraints.lon === 'number'
      ? { lat: constraints.lat, lon: constraints.lon }
      : null)
    setRadiusM(typeof constraints.radius_m === 'number' && [1000, 3000, 5000, 10000].includes(constraints.radius_m)
      ? constraints.radius_m
      : 3000)
    setSort(constraints.sort === 'distance_asc' && !(typeof constraints.lat === 'number' && typeof constraints.lon === 'number')
      ? 'relevance'
      : constraints.sort ?? 'relevance')
  }, [])

  const serviceUnavailable = health.isError || health.data?.status === 'not_ready'
  return (
    <div className="chat-app redesign-v2">
      <a className="skip-link" href="#conversation-heading">رفتن به گفتگوی خرید</a>
      {serviceUnavailable && (
        <p className="ux-connection-alert" role="status">اتصال به سرویس برقرار نیست. هنگام ارسال درخواست می‌توانی دوباره تلاش کنی.</p>
      )}

      <main className="chat-main journey-layout" id="home">
        <div className="journey-workspace">
          <MissionPanel budget={maxPriceToman} mustHaveCredit={mustHaveCredit} location={location} radiusM={radiusM} sort={sort} onLocationChange={setLocation} onRestoreConstraints={restoreMissionFilters} />
        </div>
      </main>
    </div>
  )
}
