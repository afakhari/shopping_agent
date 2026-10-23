import { afterEach, describe, expect, it, vi } from 'vitest'
import { getMission, getRoutingCapability, requestRouteEstimates, sendMissionTurn } from './mission-api'
import type { MissionEvent } from './mission-api'

afterEach(() => vi.unstubAllGlobals())

describe('API failure modes never expose raw Nginx HTML', () => {
  it.each([502, 503, 504, 429, 404])('explains HTTP %i in Persian', async (status) => {
    vi.stubGlobal('fetch', vi.fn(async () =>
      new Response('<html>upstream unavailable</html>', { status, headers: { 'Content-Type': 'text/html' } })))
    await expect(getMission('m')).rejects.toThrow(/سرور|درخواست‌ها|مأموریت/)
  })
  it('shows a meaningful error for unexpected non-JSON 200', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response('bad', { status: 200 })))
    await expect(getMission('m')).rejects.toThrow('نامعتبر')
  })
  it('preserves validated API error descriptions', async () => {
    vi.stubGlobal('fetch', vi.fn(async () =>
      new Response(JSON.stringify({ error: { message: 'این شرط معتبر نیست.' } }),
        { status: 400, headers: { 'Content-Type': 'application/json' } })))
    await expect(getMission('m')).rejects.toThrow('این شرط معتبر نیست.')
  })
})

describe('SSE stream terminal state', () => {
  const event = (type: string, seq: number): MissionEvent => ({
    schema_version: 1, mission_id: 'mission', seq, type, payload: {},
  })
  const stream = (...events: MissionEvent[]) => new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(new TextEncoder().encode(events.map((item) =>
        `data: ${JSON.stringify(item)}\n\n`).join('')))
      controller.close()
    },
  })
  it('accepts only a complete, matching turn with an actual result surface', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(
      stream(event('ui.component', 1), event('turn.completed', 2)),
      { status: 200, headers: { 'Content-Type': 'text/event-stream' } },
    )))
    const received: MissionEvent[] = []
    await sendMissionTurn('mission', 'هدفون', {}, (value) => received.push(value))
    expect(received.map((item) => item.type)).toEqual(['ui.component', 'turn.completed'])
  })
  it('rejects an interrupted event stream, not an apparent success', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(stream(event('ui.component', 1)),
      { status: 200 })))
    await expect(sendMissionTurn('mission', 'هدفون', {}, () => undefined)).rejects.toThrow('کامل')
  })
  it('rejects missing UI results even if the completion marker arrived', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(stream(event('turn.completed', 1)),
      { status: 200 })))
    await expect(sendMissionTurn('mission', 'هدفون', {}, () => undefined)).rejects.toThrow('کامل')
  })
  it('rejects a completion event without a structured payload', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(
      stream(event('ui.component', 1), { ...event('turn.completed', 2), payload: null } as unknown as MissionEvent),
      { status: 200 },
    )))
    await expect(sendMissionTurn('mission', 'هدفون', {}, () => undefined)).rejects.toThrow('کامل')
  })
  it('accepts a persisted conversational reply without fake product UI', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(stream(
      { ...event('assistant.message', 1), payload: { text: 'سلام، چطوری؟' } },
      { ...event('turn.completed', 2), payload: { intent_parser: 'local_conversation' } },
    ), { status: 200 })))
    const received: MissionEvent[] = []
    await sendMissionTurn('mission', 'احوال شما؟', {}, value => received.push(value))
    expect(received.map(item => item.type)).toEqual(['assistant.message', 'turn.completed'])
  })
  it('does not accept a forged conversational completion with no assistant reply', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(stream(
      { ...event('turn.completed', 1), payload: { intent_parser: 'local_conversation' } },
    ), { status: 200 })))
    await expect(sendMissionTurn('mission', 'احوال شما؟', {}, () => undefined)).rejects.toThrow('کامل')
  })
  it('ignores cross-mission stream frames', async () => {
    vi.stubGlobal('fetch', vi.fn(async () =>
      new Response(stream({ ...event('ui.component', 1), mission_id: 'other' },
        event('turn.completed', 2)), { status: 200 })))
    await expect(sendMissionTurn('mission', 'هدفون', {}, () => undefined)).rejects.toThrow('کامل')
  })
})


describe('Neshan route boundaries', () => {
  it('checks server capability without spending a paid routing request', async () => {
    const fetchMock = vi.fn<typeof fetch>(async () => new Response(JSON.stringify({
      provider: 'neshan', enabled: false, modes: [],
    }), { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)
    const capability = await getRoutingCapability('mission')
    expect(capability.enabled).toBe(false)
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(fetchMock.mock.calls[0]?.[1]?.method ?? 'GET').toBe('GET')
  })

  it('requires a deliberate Direction request for exactly one selected seller', async () => {
    const fetchMock = vi.fn<typeof fetch>(async () => new Response(JSON.stringify({
      provider: 'neshan', service: 'direction', mode: 'car', status: 'ok',
      route: {offer_id: 'o2', status: 'ok', duration_seconds: 420, route_distance_meters: 2000},
      estimates: [], availability_verified: false, source: 'provider_route_estimate',
    }), { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)
    const value = await requestRouteEstimates('mission', {
      service: 'direction',
      result_set_id: 'set',
      offer_ids: ['o2'], mode: 'car',
      origin: {lat: 35.7, lon: 51.4, source: 'manual_region'},
    })
    expect(value.route?.offer_id).toBe('o2')
    expect(value.route?.duration_seconds).toBe(420)
    const input = JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body))
    expect(input.service).toBe('direction')
    expect(input.offer_ids).toEqual(['o2'])
    expect(value.availability_verified).toBe(false)
  })

  it('sends only scoped offer IDs and the explicitly chosen Tehran origin', async () => {
    const fetchMock = vi.fn<typeof fetch>(async () => new Response(JSON.stringify({
      provider: 'neshan', mode: 'car', status: 'unavailable', reason: 'not_configured',
      estimates: [], availability_verified: false, source: 'provider_route_estimate',
    }), { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)
    const value = await requestRouteEstimates('m1', {
      result_set_id: 'current', origin: { lat: 35.7, lon: 51.4, source: 'manual_region' },
      offer_ids: ['o1', 'o2'], mode: 'car',
    })
    expect(value.estimates).toEqual([])
    expect(value.status).toBe('unavailable')
    const options = fetchMock.mock.calls[0]?.[1]
    expect(options?.method).toBe('POST')
    expect(JSON.parse(String(options?.body))).toEqual({
      result_set_id: 'current', origin: { lat: 35.7, lon: 51.4, source: 'manual_region' },
      offer_ids: ['o1', 'o2'], mode: 'car',
    })
  })
})
