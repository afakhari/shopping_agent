import { afterEach, describe, expect, it, vi } from 'vitest'
import { getMission, sendMissionTurn } from './mission-api'
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
