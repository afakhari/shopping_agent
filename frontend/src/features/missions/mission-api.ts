import type { CatalogOffer, CatalogSearchResult } from '../search/catalog-api'

export interface MissionConstraints {
  city?: 'tehran'
  max_price_toman?: string | null
  must_have_in_person_credit?: boolean
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
  outcome: 'confirmed_available' | 'unavailable' | 'no_answer' | 'closed' | 'error'
  response_text: string
  source_type: 'demo_simulation'
  scenario_index: number
  created_at: string
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

async function readJson<T>(response: Response): Promise<T> {
  const payload = (await response.json()) as T & ApiErrorBody
  if (!response.ok) {
    throw new Error(payload.error?.message ?? `درخواست با خطای ${response.status} مواجه شد.`)
  }
  return payload
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
    let messageText = `پردازش مأموریت با خطای ${response.status} مواجه شد.`
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

  const dispatchBlock = (block: string) => {
    const dataLines = block.split(/\r?\n/).filter((line) => line.startsWith('data:'))
    if (!dataLines.length) return
    const raw = dataLines.map((line) => line.slice(5).trimStart()).join('\n')
    if (!raw) return
    try {
      const event = JSON.parse(raw) as MissionEvent
      if (event && typeof event.seq === 'number' && typeof event.type === 'string') onEvent(event)
    } catch {
      // Ignore malformed event blocks; the persistent mission snapshot remains recoverable.
    }
  }

  try {
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const blocks = buffer.split(/\r?\n\r?\n/)
      buffer = blocks.pop() ?? ''
      for (const block of blocks) dispatchBlock(block)
    }
    buffer += decoder.decode()
    if (buffer.trim()) dispatchBlock(buffer)
  } finally {
    reader.releaseLock()
  }
}

export async function createContactAttempt(
  missionId: string,
  input: { shopId: string; offerId: string; purpose?: 'verify_availability' | 'verify_price' | 'verify_hours' },
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
