import { describe, expect, it } from 'vitest'
import type { CatalogProduct } from '../search/catalog-api'
import { buildComparisonSpecColumns } from './comparison-specs'

const product = (id: string, specs: CatalogProduct['specs']): CatalogProduct => ({
  id, title: id, brand: null, category: 'هدفون', model: null, images: [], specs,
})

describe('category-specific comparison', () => {
  it('compares shared factual attributes rather than inventing technical specifications', () => {
    const data = buildComparisonSpecColumns([
      product('a', [{ key: 'رنگ', value: 'مشکی' }, { key: 'وزن', value: '۱۰۰ گرم' }]),
      product('b', [{ key: 'رنگ', value: 'سفید' }]),
    ])
    expect(data.columns.map((c) => c.label)).toEqual(['رنگ'])
    expect(data.valuesByProduct[0].spec_0).toBe('مشکی')
    expect(data.valuesByProduct[1].spec_0).toBe('سفید')
  })

  it('uses unknown for missing values when two of three products have the attribute', () => {
    const data = buildComparisonSpecColumns([
      product('a', [{ key: 'باتری', value: '۴ ساعت' }]),
      product('b', [{ key: 'باتری', value: '۶ ساعت' }]),
      product('c', []),
    ])
    expect(data.columns[0].label).toBe('باتری')
    expect(data.valuesByProduct[2].spec_0).toBe('نامشخص')
  })

  it('ignores unshared irrelevant product-title attributes', () => {
    const data = buildComparisonSpecColumns([
      product('a', [{ key: 'نام محصول', value: 'a' }]),
      product('b', [{ key: 'نام محصول', value: 'b' }]),
    ])
    expect(data.columns).toEqual([])
  })
})
