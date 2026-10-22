import { describe, expect, it } from 'vitest'
import { findCurrentSearchMessage, shouldFollowConversation } from './conversation-behavior'

describe('context-first shopping UX', () => {
  it('keeps product results actionable through a purely conversational follow-up', () => {
    const results = { role: 'assistant', results: [{ id: 'product-1' }] }
    const followup = { role: 'assistant' }
    expect(findCurrentSearchMessage([results, followup])).toBe(results)
  })

  it('respects a new empty-result response instead of presenting stale products as current', () => {
    const old = { role: 'assistant', results: [{ id: 'product-1' }] }
    const empty = { role: 'assistant', results: [] }
    expect(findCurrentSearchMessage([old, empty])).toBe(empty)
  })

  it('only follows new messages when the reader is near the conversation end', () => {
    expect(shouldFollowConversation(1000, 700, 240)).toBe(true)
    expect(shouldFollowConversation(1000, 150, 240)).toBe(false)
  })
})
