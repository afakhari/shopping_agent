import { describe, expect, it } from 'vitest'
import { classifyLocalConversation, isAssistantHelpRequest, isGreetingOnly } from './greeting-intent'

describe('local conversational intent never wastes an LLM purchase request', () => {
  it.each([
    ['سلام', 'greeting'], ['سلام!', 'greeting'], ['درود', 'greeting'],
    ['سلام، خوبی؟', 'greeting'], ['چطوری', 'greeting'], ['چطوری؟', 'greeting'],
    ['خوبی؟', 'greeting'], ['چه خبر؟', 'greeting'], ['احوال شما؟', 'greeting'],
    ['احوالِ شما؟؟', 'greeting'], ['احوالتون چطوره؟', 'greeting'], ['سلام، حال شما چطوره؟', 'greeting'],
    ['حالِ شما چطور است؟', 'greeting'], ['حال شما خوبه؟', 'greeting'],
    ['احوال شما امروز چطوره؟', 'greeting'],
    ['شما چطورید؟', 'greeting'], ['حالتون خوبه؟', 'greeting'],
    ['صبح بخیر', 'greeting'],
    ['Hi', 'greeting'], ['hello', 'greeting'], ['سلام عليكم', 'greeting'],
    ['راهنما', 'help'], ['چطور ازت استفاده کنم؟', 'help'], ['چطور باهات کار کنم؟', 'help'],
    ['چطوری کار می‌کنی؟', 'help'], ['روش استفاده', 'help'],
    ['مرسی', 'thanks'], ['خیلی ممنون', 'thanks'], ['خداحافظ!', 'goodbye'], ['بای', 'goodbye'],
  ] as const)('recognizes %s as %s', (message, intent) => {
    expect(classifyLocalConversation(message)).toBe(intent)
  })

  it.each([
    'سلام هدفون می‌خوام', 'سلام لپ تاپ زیر ۲۰ میلیون', 'درود یک گوشی معرفی کن',
    'هدفون', '', 'چطور هدفون مناسب بخرم؟', 'راهنمای خرید هدفون بی‌سیم',
    'هدفون تا ۳ میلیون', 'چطوری یه لپ تاپ خوب انتخاب کنم',
    'سلام گوشی سامسونگ می‌خوام', 'ممنون، حالا فشارسنج معرفی کن',
    'چطور خرید قسطی حضوری انجام بدم؟',
    'کمک می‌خوام برای خرید لپ‌تاپ',
    'چجوری گوشی دوربین خوب پیدا کنم',
    'احوال شما، یک هدفون تا سه میلیون معرفی کن',
    'شما چطورید و گوشی مناسب می شناسی؟',
    'چه خبر از قیمت لپ تاپ های گیمینگ؟',
  ])('does not swallow a purchase request: %s', (message) => {
    expect(classifyLocalConversation(message)).toBeNull()
    expect(isAssistantHelpRequest(message)).toBe(false)
    expect(isGreetingOnly(message)).toBe(false)
  })
  it('handles Arabic Persian letter variants, spacing and invisible separators', () => {
    expect(classifyLocalConversation('سَلام')).toBe('greeting')
    expect(classifyLocalConversation('سلام\u200c،  چطوری؟؟')).toBe('greeting')
    expect(classifyLocalConversation('چطور كار مي\u200cكني؟')).toBe('help')
  })
  it('does not classify arbitrary long or injected messages as greetings', () => {
    expect(classifyLocalConversation('سلام ' + 'هدفون '.repeat(90))).toBeNull()
  })
})
