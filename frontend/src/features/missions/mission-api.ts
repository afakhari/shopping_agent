import type { CatalogOffer, CatalogSearchResult } from '../search/catalog-api'

export interface MissionConstraints {
  city?: 'tehran'
  max_price_toman?: string | null
  must_have_in_person_credit?: boolean
  brand_name?: string | null
  model_exact?: string | null
  lat?: number
  lon?: number
  radius_m?: number
  sort?: 'relevance' | 'price_asc' | 'distance_asc' | 'recent_price_change'
}

export interface MissionSnapshot {
  mission_id: string
  status: string
  current_stage: string
  initial_message: string
  constraints: MissionConstraints
  state?: Record<string, unknown>
  events?: MissionEvent[]
  last_event_seq: number
}

export interface MissionEvent {
  schema_version: 1
  mission_id: string
  seq: number
  type: string
  payload: Record<string, unknown>
}

export interface ContactAttemptRecord {
  id: string
  shop_id: string
  shop_name: string
  offer_id: string
  purpose: string
  outcome: 'confirmed_available' | 'unavailable' | 'no_answer' | 'closed' | 'error' | 'price_changed'
  response_text: string
  source_type: 'demo_simulation'
  scenario_index: number
  created_at: string
  requested_questions?: Array<'stock' | 'price' | 'hours'>
  evidence?: {
    stock?: { status: string; source: string; verified_in_real_world: boolean }
    price?: {
      status: string
      registered_price_toman: string | null
      last_price_changed_at: string | null
      source: string
      verified_in_real_world: boolean
    }
    hours?: {
      status: string
      weekly_hours: string
      opening_status: { status: string; label: string }
      source: string
      verified_in_real_world: boolean
    }
  }
}

export interface ContactAttemptResponse {
  attempt: ContactAttemptRecord
  alternatives: CatalogOffer[]
  alternative_products: CatalogSearchResult[]
  events?: MissionEvent[]
}

interface ApiErrorBody {
  error?: { code?: string; message?: string; details?: unknown }
}

function friendlyHttpError(status: number): string {
  if (status === 429) return 'تعداد درخواست‌ها بیش از حد مجاز است. بعداً دوباره تلاش کن.'
  if (status === 502 || status === 503 || status === 504)
    return 'ارتباط با سرور موقتاً برقرار نیست. درخواست را دوباره نفرست؛ ابتدا وضعیت ذخیره‌شده را بررسی کن.'
  if (status === 401 || status === 403 || status === 404)
    return 'دسترسی به این مأموریت ممکن نیست. شاید نشست مرورگر منقضی شده باشد.'
  return `درخواست با خطای ${status} مواجه شد.`
}

async function readJson<T>(response: Response): Promise<T> {
  const body = await response.text()
  let payload: unknown = null
  try { payload = JSON.parse(body) } catch { /* Nginx may return an HTML error page. */ }
  if (!response.ok) {
    const serverMessage = payload && typeof payload === 'object'
      ? (payload as ApiErrorBody).error?.message : null
    throw new Error(serverMessage || friendlyHttpError(response.status))
  }
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
    throw new Error('پاسخ سرور ناقص یا نامعتبر است. وضعیت مأموریت را دوباره بررسی کن.')
  }
  return payload as T
}

export async function createMission(
  initialMessage: string,
  constraints: MissionConstraints,
  signal?: AbortSignal,
): Promise<MissionSnapshot> {
  const response = await fetch('/api/v1/missions/', {
    method: 'POST',
    signal,
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({ initial_message: initialMessage, constraints }),
  })
  return readJson<MissionSnapshot>(response)
}

export async function getMission(
  missionId: string,
  signal?: AbortSignal,
): Promise<MissionSnapshot> {
  const response = await fetch(`/api/v1/missions/${encodeURIComponent(missionId)}/`, {
    method: 'GET',
    signal,
    headers: { Accept: 'application/json' },
  })
  return readJson<MissionSnapshot>(response)
}

export async function sendMissionTurn(
  missionId: string,
  message: string,
  constraints: MissionConstraints,
  onEvent: (event: MissionEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(`/api/v1/missions/${encodeURIComponent(missionId)}/turns/`, {
    method: 'POST',
    signal,
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
    body: JSON.stringify({ message, constraints }),
  })
  if (!response.ok) {
    let messageText = friendlyHttpError(response.status)
    try {
      const bodyText = await response.text()
      // DRF encodes errors negotiated as text/event-stream as a single `data:` frame.
      const jsonText = bodyText.trim().startsWith('data:')
        ? bodyText.trim().slice(5).trim()
        : bodyText
      const payload = JSON.parse(jsonText) as ApiErrorBody
      messageText = payload.error?.message ?? messageText
    } catch {
      // Keep the HTTP fallback when the error body is neither JSON nor an SSE JSON frame.
    }
    throw new Error(messageText)
  }
  if (!response.body) throw new Error('پاسخ جریانی از سرور دریافت نشد.')

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let gotCompletion = false
  let gotResultSurface = false
  let gotAssistantMessage = false
  let gotConversationalCompletion = false

  const dispatchBlock = (block: string) => {
    const dataLines = block.split(/\r?\n/).filter((line) => line.startsWith('data:'))
    if (!dataLines.length) return
    const raw = dataLines.map((line) => line.slice(5).trimStart()).join('\n')
    if (!raw) return
    try {
      const event = JSON.parse(raw) as MissionEvent
      if (event && Number.isSafeInteger(event.seq) && typeof event.type === 'string'
        && event.mission_id === missionId && event.schema_version === 1
        && event.payload && typeof event.payload === 'object' && !Array.isArray(event.payload)) {
        if (event.type === 'ui.component') gotResultSurface = true
        if (event.type === 'assistant.message' && typeof event.payload.text === 'string'
          && Boolean(event.payload.text.trim())) gotAssistantMessage = true
        if (event.type === 'turn.completed') {
          gotCompletion = true
          if (event.payload.intent_parser === 'local_conversation' || event.payload.intent_parser === 'contextual') {
            gotConversationalCompletion = true
          }
        }
        onEvent(event)
      }
    } catch {
      // Ignore malformed event blocks; the persistent mission snapshot remains recoverable.
    }
  }

  try {
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      if (buffer.length > 2_000_000) throw new Error('پاسخ جریانی بیش از حد بزرگ است؛ وضعیت ذخیره‌شده را بررسی کن.')
      const blocks = buffer.split(/\r?\n\r?\n/)
      buffer = blocks.pop() ?? ''
      for (const block of blocks) dispatchBlock(block)
    }
    buffer += decoder.decode()
    if (buffer.trim()) dispatchBlock(buffer)
    if (!gotCompletion || (!gotResultSurface && !(gotConversationalCompletion && gotAssistantMessage))) {
      throw new Error('پاسخ جریانی کامل نرسید؛ قبل از ارسال دوباره، نتیجه ذخیره‌شده بررسی می‌شود.')
    }
  } finally {
    reader.releaseLock()
  }
}

export interface MissionFocusAction {
  action: 'select_product' | 'view_sellers' | 'view_products' | 'select_offer'
  result_set_id: string
  product_id?: string
  offer_id?: string
  offer_ids?: string[]
}

export interface MissionFocusResponse {
  state: Record<string, unknown>
  last_event_seq: number
  events: MissionEvent[]
}

export async function updateMissionFocus(
  missionId: string,
  action: MissionFocusAction,
  signal?: AbortSignal,
): Promise<MissionFocusResponse> {
  const response = await fetch(`/api/v1/missions/${encodeURIComponent(missionId)}/focus/`, {
    method: 'POST',
    signal,
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify(action),
  })
  return readJson<MissionFocusResponse>(response)
}

export async function createContactAttempt(
  missionId: string,
  input: { shopId: string; offerId: string; purpose?: 'verify_availability' | 'verify_price' | 'verify_hours'; questions?: Array<'stock' | 'price' | 'hours'>; clientRequestId?: string },
  signal?: AbortSignal,
): Promise<ContactAttemptResponse> {
  const response = await fetch(`/api/v1/missions/${encodeURIComponent(missionId)}/contact-attempts/`, {
    method: 'POST',
    signal,
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({
      shop_id: input.shopId,
      offer_id: input.offerId,
      purpose: input.purpose ?? 'verify_availability',
      questions: input.questions ?? ['stock', 'price', 'hours'],
      client_request_id: input.clientRequestId ?? globalThis.crypto.randomUUID(),
    }),
  })
  return readJson<ContactAttemptResponse>(response)
}

export function isProductResultPayload(value: unknown): value is { results: CatalogSearchResult[]; total: number; query?: string } {
  if (!value || typeof value !== 'object') return false
  const candidate = value as { results?: unknown; total?: unknown; query?: unknown }
  return Array.isArray(candidate.results) && typeof candidate.total === 'number'
    && (candidate.query === undefined || typeof candidate.query === 'string')
}
