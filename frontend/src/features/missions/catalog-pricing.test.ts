import { describe, expect, it } from 'vitest'
import { formatCatalogPrice } from './catalog-pricing'

describe('catalog price evidence formatting', () => {
  it('formats integer and serialized Decimal prices consistently', () => {
    expect(formatCatalogPrice('1250000')).toContain('۱٬۲۵۰٬۰۰۰')
    expect(formatCatalogPrice('1250000.00')).toBe(formatCatalogPrice('1250000'))
  })
  it('never silently truncates fractional or malformed values', () => {
    expect(formatCatalogPrice('1250000.20')).toBe('قیمت نامشخص')
    expect(formatCatalogPrice('bad')).toBe('قیمت نامشخص')
    expect(formatCatalogPrice('')).toBe('قیمت ثبت نشده')
    expect(formatCatalogPrice(null)).toBe('قیمت ثبت نشده')
  })
  it('keeps zero and very large integers safe', () => {
    expect(formatCatalogPrice('0')).toContain('۰')
    expect(formatCatalogPrice('9999999999999999999')).toContain('تومان')
  })
})
