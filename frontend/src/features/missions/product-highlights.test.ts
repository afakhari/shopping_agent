import { describe, expect, it } from 'vitest'
import { chooseProductHighlights } from './product-highlights'
import type { CatalogProduct } from '../search/catalog-api'

const product = (specs: CatalogProduct['specs'], category = 'هدفون'): CatalogProduct =>
  ({ id: 'p1', title: 'کالای نمونه', brand: null, category, model: null, images: [], specs })

describe('catalog-grounded shopping highlights', () => {
  it('prioritizes decision-making headphone specs over generic details', () => {
    const highlights = chooseProductHighlights(product([
      { key: 'رنگ', value: 'مشکی' },
      { key: 'نوع اتصال', value: 'بی‌سیم' },
      { key: 'شارژ باتری', value: '۱۲ ساعت' },
      { key: 'وزن', value: '۲۳۰ گرم' },
    ]))
    expect(highlights).toEqual([{key:'شارژ باتری',value:'۱۲ ساعت'}, {key:'نوع اتصال',value:'بی‌سیم'}])
  })
  it('favors useful size and type evidence for general shopping categories', () => {
    const highlights = chooseProductHighlights(product([
      {key:'کشور سازنده',value:'ایران'},
      {key:'سایز کابل',value:'۲٫۵ میلی‌متر'},
      {key:'نوع کابل',value:'افشان'},
    ],'سیم و کابل برق ساختمان'))
    expect(highlights.map(item=>item.key)).toEqual(['سایز کابل','نوع کابل'])
  })

  it('does not invent values and ignores empty or placeholder specs', () => {
    expect(chooseProductHighlights(product([
      { key: 'باتری', value: 'نامشخص' }, { key: 'مدل', value: 'ساختگی' }, { key: 'رنگ', value: 'سفید' },
    ]))).toEqual([{key:'رنگ',value:'سفید'}])
    expect(chooseProductHighlights(product([]))).toEqual([])
  })
  it('handles duplicate fields and three-spec maximum without mutating source', () => {
    const specs = [{key:'رم',value:'۱۶ گیگابایت'},{key:'رم',value:'۸ گیگابایت'},{key:'پردازنده',value:'i5'},{key:'وزن',value:'۱ کیلوگرم'}]
    const highlights = chooseProductHighlights(product(specs,'لپ تاپ'),5)
    expect(highlights).toHaveLength(3)
    expect(highlights[0]?.key).toBe('پردازنده')
    expect(specs).toHaveLength(4)
  })
})
