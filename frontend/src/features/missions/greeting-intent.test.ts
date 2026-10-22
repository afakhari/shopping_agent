import { describe, expect, it } from 'vitest'
import { isGreetingOnly } from './greeting-intent'

describe('greeting-only UX', () => {
  it.each(['سلام', 'سلام!', 'درود', 'سلام، خوبی؟', 'صبح بخیر', 'Hi', 'hello'])(
    'recognizes the conversational greeting %s', (message) => {
      expect(isGreetingOnly(message)).toBe(true)
    },
  )
  it.each(['سلام هدفون می‌خوام', 'سلام لپ تاپ زیر ۲۰ میلیون', 'درود یک گوشی معرفی کن', 'هدفون', ''])(
    'never hides a product query %s', (message) => {
      expect(isGreetingOnly(message)).toBe(false)
    },
  )
})
