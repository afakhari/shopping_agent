import { describe, expect, it } from 'vitest'
import { buildComparisonFields, visibleComparisonFields } from './comparison-view'

describe('mobile product comparison', () => {
  const cols = [{key:'product',label:'محصول'},{key:'price',label:'قیمت'},{key:'spec_0',label:'حافظه'},{key:'spec_1',label:'نوع اتصال'}]
  const rows = [
    {product:'الف',price:'۸۰۰ هزار',spec_0:'۱۶ گیگ',spec_1:'بلوتوث'},
    {product:'ب',price:'۹۰۰ هزار',spec_0:'۸ گیگ',spec_1:'بلوتوث'},
  ]
  it('compares by feature and hides identical attributes by default', () => {
    const fields = buildComparisonFields(cols,rows)
    expect(fields.map(field=>field.label)).toEqual(['قیمت','حافظه','نوع اتصال'])
    expect(visibleComparisonFields(fields,true).map(field=>field.label)).toEqual(['قیمت','حافظه'])
    expect(visibleComparisonFields(fields,false)).toHaveLength(3)
  })
  it('keeps offer price and merchant facts even if identical', () => {
    const f = buildComparisonFields([{key:'product',label:'محصول'}, {key:'shop',label:'فروشگاه'}, {key:'price',label:'قیمت'}], [{product:'الف',shop:'الف',price:'۱۰۰'}, {product:'ب',shop:'الف',price:'۱۰۰'}])
    expect(visibleComparisonFields(f,true)).toHaveLength(2)
  })
  it('uses explicit missing data rather than fabricated equality', () => {
    const f = buildComparisonFields([{key:'spec_0',label:'باتری'}],[{spec_0:'۱۰ ساعت'},{}])
    expect(f[0]?.different).toBe(true)
    expect(f[0]?.values).toEqual(['۱۰ ساعت','ثبت نشده'])
  })
})
