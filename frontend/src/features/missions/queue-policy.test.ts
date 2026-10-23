import { describe, expect, it } from 'vitest'
import { canDrainQueuedTurn } from './queue-policy'

describe('sequential chat recovery', () => {
  it('holds followups after a network error until a committed response is known', () => {
    expect(canDrainQueuedTurn(false, false)).toBe(false)
    expect(canDrainQueuedTurn(false, true)).toBe(false)
    expect(canDrainQueuedTurn(true, true)).toBe(false)
  })

  it('drains only after a confirmed turn and no pending recovery', () => {
    expect(canDrainQueuedTurn(true, false)).toBe(true)
  })
})
