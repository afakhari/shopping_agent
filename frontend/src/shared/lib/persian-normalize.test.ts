import { describe, expect, it } from 'vitest'
import { normalizePersianSearchText } from './persian-normalize'

describe('normalizePersianSearchText', () => {
  it('normalizes Arabic Yeh and Kaf', () => {
    expect(normalizePersianSearchText('كیف ياس')).toBe('کیف یاس')
  })

  it('converts Persian and Arabic digits to ASCII', () => {
    expect(normalizePersianSearchText('بودجه ۱۲۳ و ٤٥')).toBe('بودجه 123 و 45')
  })

  it('normalizes whitespace and zero-width non-joiners for matching', () => {
    expect(normalizePersianSearchText('گوشی‌ همراه   تهران')).toBe('گوشی همراه تهران')
  })

  it('preserves empty input as an empty string', () => {
    expect(normalizePersianSearchText('  ')).toBe('')
  })
})
