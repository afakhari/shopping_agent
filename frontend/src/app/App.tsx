import { useQuery } from '@tanstack/react-query'
import { useCallback, useEffect, useState } from 'react'
import { ArrowUpLeft, Compass, MapPin, Search, Store, ShieldCheck, Route, Sparkles } from 'lucide-react'
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

  const serviceStatus = health.data?.status === 'ready'
    ? 'online'
    : health.isError || health.data?.status === 'not_ready'
      ? 'offline'
      : 'checking'
  return (
    <div className="chat-app redesign-v2">
      <a className="skip-link" href="#conversation-heading">رفتن به گفتگوی خرید</a>
      <header className="chat-topbar">
        <div className="chat-topbar-inner">
          <a className="chat-brand" href="#home" aria-label="بازارکامپس، دستیار خرید">
            <span className="chat-brand-mark"><Compass size={21} strokeWidth={2.3} /></span>
            <span className="chat-brand-copy"><strong>بازارکامپس</strong><small>دستیار هوشمند خرید حضوری</small></span>
          </a>
          <div className="chat-topbar-status">
            <span className="chat-location"><MapPin size={14} /> تهران</span>
            <span className={`chat-service-status ${serviceStatus}`} aria-live="polite">
              <i />
              {serviceStatus === 'online' ? 'دستیار آماده' : serviceStatus === 'offline' ? 'اتصال برقرار نیست' : 'در حال اتصال'}
            </span>
          </div>
        </div>
      </header>

      <main className="chat-main journey-layout" id="home">
        <aside className="journey-sidebar" aria-label="راهنمای مسیر خرید">
          <div className="journey-sidebar-top">
            <span className="journey-sidebar-eyebrow"><Sparkles size={15} /> همراه تو در انتخاب</span>
            <h2>خرید خوب، از یک سؤال خوب شروع می‌شود.</h2>
            <p>نیازت را بگو؛ از پیدا کردن مدل تا انتخاب فروشگاه و برنامه مراجعه کنارت هستیم.</p>
          </div>
          <nav className="journey-steps" aria-label="مراحل راهنمای خرید">
            <p className="journey-section-label">مسیر خرید</p>
            <ol>
              <li><span className="journey-step-icon"><Search size={17} /></span><span><strong>شناخت نیاز</strong><small>بودجه و ویژگی‌های مهم</small></span><b>۰۱</b></li>
              <li><span className="journey-step-icon"><Store size={17} /></span><span><strong>کالا و فروشگاه</strong><small>مقایسه مدل‌ها و قیمت‌ها</small></span><b>۰۲</b></li>
              <li><span className="journey-step-icon"><ShieldCheck size={17} /></span><span><strong>بررسی فروشنده</strong><small>استعلام شبیه‌سازی‌شده</small></span><b>۰۳</b></li>
              <li><span className="journey-step-icon"><Route size={17} /></span><span><strong>آمادگی مراجعه</strong><small>نشانی و گزینه پشتیبان</small></span><b>۰۴</b></li>
            </ol>
          </nav>
          <div className="journey-side-note">
            <div className="journey-side-note-icon"><ShieldCheck size={19} /></div>
            <strong>شفافیت، قبل از خرید</strong>
            <p>قیمت‌ها از دیتاست ثبت‌شده هستند؛ موجودی فروشگاه در این نسخه به‌صورت نمایشی بررسی می‌شود.</p>
            <a href="#conversation-composer">شروع گفتگوی خرید <ArrowUpLeft size={15} aria-hidden="true" /></a>
          </div>
          <p className="journey-sidebar-footer">نسخه آزمایشی · پوشش داده‌های فروشگاهی تهران</p>
        </aside>
        <div className="journey-workspace">
          <div className="journey-mobile-ribbon" aria-label="مراحل خرید">
            <span><Search size={14} /> انتخاب</span>
            <span className="journey-ribbon-divider" aria-hidden="true" />
            <span><Store size={14} /> مقایسه</span>
            <span className="journey-ribbon-divider" aria-hidden="true" />
            <span><Route size={14} /> مراجعه</span>
          </div>
          <MissionPanel budget={maxPriceToman} mustHaveCredit={mustHaveCredit} location={location} radiusM={radiusM} sort={sort} onLocationChange={setLocation} onRestoreConstraints={restoreMissionFilters} />
        </div>
      </main>
    </div>
  )
}
