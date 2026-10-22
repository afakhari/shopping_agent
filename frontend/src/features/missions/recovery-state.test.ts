import { describe, expect, it } from 'vitest'
import { completedTurnWasPersisted } from './recovery-state'
import type { MissionSnapshot } from './mission-api'

const build = (lastMessage: string, seq: number, type = 'turn.completed'): MissionSnapshot => ({
  mission_id: 'mission', status: 'waiting_for_user', current_stage: 'results_ready',
  initial_message: 'هدفون', last_event_seq: seq, constraints: {},
  state: { last_turn_message: lastMessage },
  events: [{ schema_version: 1, mission_id: 'mission', seq, type, payload: {} }],
})

describe('recovery after an interrupted HTTP stream', () => {
  it('recognizes only the newly persisted, matching turn', () => {
    expect(completedTurnWasPersisted(build('هدفون', 15), 'هدفون', 10)).toBe(true)
    expect(completedTurnWasPersisted(build('گوشی', 15), 'هدفون', 10)).toBe(false)
    expect(completedTurnWasPersisted(build('هدفون', 9), 'هدفون', 10)).toBe(false)
    expect(completedTurnWasPersisted(build('هدفون', 15, 'stage'), 'هدفون', 10)).toBe(false)
  })
  it('fails closed when snapshot lacks event history', () => {
    const snapshot = build('هدفون', 15)
    delete snapshot.events
    expect(completedTurnWasPersisted(snapshot, 'هدفون', 10)).toBe(false)
  })
})
