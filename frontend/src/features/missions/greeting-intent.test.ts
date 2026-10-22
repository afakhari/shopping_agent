import { describe, expect, it } from 'vitest'
import { isAssistantHelpRequest, isGreetingOnly } from './greeting-intent'

describe('greeting-only UX', () => {
  it.each(['سلام', 'سلام!', 'درود', 'سلام، خوبی؟', 'چطوری', 'چطوری؟', 'خوبی؟', 'چه خبر؟', 'صبح بخیر', 'Hi', 'hello'])(
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

describe('onboarding help versus real purchase intent', () => {
  it.each(['راهنما', 'چطور ازت استفاده کنم؟', 'چطور باهات کار کنم؟', 'چطوری کار می‌کنی؟'])(
    'keeps %s out of the product catalogue search', (message) => {
      expect(isAssistantHelpRequest(message)).toBe(true)
    },
  )
  it.each([
    'چطور هدفون مناسب بخرم؟',
    'راهنمای خرید هدفون بی‌سیم',
    'هدفون تا ۳ میلیون',
    'چطوری یه لپ تاپ خوب انتخاب کنم',
    'سلام گوشی سامسونگ می‌خوام',
    '',
  ])('does not classify a product-shopping question as help: %s', (message) => {
    expect(isAssistantHelpRequest(message)).toBe(false)
    expect(isGreetingOnly(message)).toBe(false)
  })
})
