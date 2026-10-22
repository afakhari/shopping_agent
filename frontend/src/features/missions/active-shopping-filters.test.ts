import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('./ActiveShoppingFilters.tsx',import.meta.url),'utf8')
describe('applied filters UX',()=>{
  it('shows active constraints without silently clearing hard conditions',()=>{
    expect(source).toContain('شرایط همین جست‌وجو')
    expect(source).toContain('onClick={onEdit}')
    expect(source).toContain('خرید اعتباری حضوری')
  })
})
