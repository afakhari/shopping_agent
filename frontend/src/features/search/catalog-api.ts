export type CatalogSort = 'relevance' | 'price_asc' | 'recent_price_change'

export interface CatalogSearchParams {
  q: string
  maxPriceToman?: string
  mustHaveInPersonCredit: boolean
  sort: CatalogSort
  page?: number
}

export interface ProductSpec {
  key?: string
  section?: string
  value?: string
}

export interface CatalogProduct {
  id: string
  title: string
  brand: string | null
  category: string | null
  model: string | null
  images: string[]
  specs: ProductSpec[]
}

export interface CatalogShop {
  id: string
  name: string
  address: string | null
  location_label: string | null
  lat: number | null
  lon: number | null
  distance_m: number | null
  accepts_in_person_credit: boolean
  opening_status?: {
    status: 'open' | 'closed' | 'unknown'
    label: string
    source: string
    checked_at: string
  }
  indoor_hints?: { mall?: string; floor?: string; unit?: string }
}

export interface CatalogOffer {
  id: string
  price_toman: string | null
  last_price_changed_at: string | null
  price_quality: 'recent_change' | 'stale' | 'unknown_timestamp' | 'unknown_price'
  seller_title?: string | null
  warranty?: {
    provider?: string | null
    description?: string | null
    period_months?: number | null
  } | null
  in_person_credit_eligible?: boolean
  shop: CatalogShop
}

export interface CatalogSearchResult {
  product: CatalogProduct
  best_offer: CatalogOffer
  eligible_offers_count: number
  reasons: string[]
}

export interface CatalogSearchResponse {
  query: string
  filters: {
    max_price_toman: string | null
    must_have_in_person_credit: boolean
    lat: number | null
    lon: number | null
    radius_m: number | null
    sort: string
  }
  page: number
  page_size: number
  total: number
  results: CatalogSearchResult[]
  intent_hint?: {
    label: string
    message: string
    alternative_label: string
    alternative_query: string
  } | null
}

interface ApiErrorBody {
  error?: { message?: string; code?: string }
}

export async function searchCatalog(
  params: CatalogSearchParams,
  signal?: AbortSignal,
): Promise<CatalogSearchResponse> {
  const query = new URLSearchParams({ q: params.q, sort: params.sort, page: String(params.page ?? 1), page_size: '12' })
  const budget = params.maxPriceToman?.trim()
  if (budget) query.set('max_price_toman', budget)
  if (params.mustHaveInPersonCredit) query.set('must_have_in_person_credit', 'true')

  const response = await fetch(`/api/v1/catalog/search/?${query.toString()}`, {
    signal,
    headers: { Accept: 'application/json' },
  })
  const payload = (await response.json()) as CatalogSearchResponse & ApiErrorBody
  if (!response.ok) {
    throw new Error(payload.error?.message ?? `جست‌وجو با خطای ${response.status} مواجه شد.`)
  }
  return payload
}


export interface ProductOffersResponse {
  product: CatalogProduct
  page: number
  page_size: number
  total: number
  results: CatalogOffer[]
}

export async function getProductOffers(
  productId: string,
  params: {
    maxPriceToman: string
    mustHaveInPersonCredit: boolean
    location?: { lat: number; lon: number } | null
    radiusM?: number
    sort?: 'relevance' | 'price_asc' | 'distance_asc' | 'recent_price_change'
    page?: number
    pageSize?: number
  },
  signal?: AbortSignal,
): Promise<ProductOffersResponse> {
  const query = new URLSearchParams({
    page: String(params.page ?? 1),
    page_size: String(params.pageSize ?? 8),
    sort: params.sort ?? 'relevance',
  })
  const budget = params.maxPriceToman.trim()
  if (budget) query.set('max_price_toman', budget)
  if (params.mustHaveInPersonCredit) query.set('must_have_in_person_credit', 'true')
  if (params.location) {
    query.set('lat', String(params.location.lat))
    query.set('lon', String(params.location.lon))
    if (params.radiusM) query.set('radius_m', String(params.radiusM))
  }

  const response = await fetch(`/api/v1/products/${encodeURIComponent(productId)}/offers/?${query.toString()}`, {
    signal,
    headers: { Accept: 'application/json' },
  })
  const payload = (await response.json()) as ProductOffersResponse & ApiErrorBody
  if (!response.ok) {
    throw new Error(payload.error?.message ?? `مقایسه فروشگاه‌ها با خطای ${response.status} مواجه شد.`)
  }
  return payload
}
