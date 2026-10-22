import type { CatalogProduct } from '../search/catalog-api'

type Column = { key: string; label: string }

/** Match category-specific factual attributes, never infer missing specifications. */
export function buildComparisonSpecColumns(products: CatalogProduct[], maxColumns = 5): {
  columns: Column[]
  valuesByProduct: Array<Record<string, string>>
} {
  const byProduct = products.map((product) => {
    const values = new Map<string, string>()
    for (const spec of product.specs ?? []) {
      const key = typeof spec.key === 'string' ? spec.key.trim() : ''
      const value = typeof spec.value === 'string' ? spec.value.trim() : ''
      if (!key || !value || key.length > 75 || value.length > 220) continue
      if (['نام محصول', 'عنوان محصول', 'کد محصول'].includes(key)) continue
      if (!values.has(key)) values.set(key, value)
    }
    return values
  })
  if (byProduct.length < 2) return { columns: [], valuesByProduct: byProduct.map(() => ({})) }

  const candidates = new Map<string, { count: number; values: Set<string> }>()
  for (const product of byProduct) {
    for (const [key, value] of product) {
      const existing = candidates.get(key) ?? { count: 0, values: new Set<string>() }
      existing.count += 1
      existing.values.add(value)
      candidates.set(key, existing)
    }
  }
  const keys = [...candidates.entries()]
    .filter(([, value]) => value.count >= 2)
    .sort((a, b) =>
      b[1].values.size - a[1].values.size ||
      b[1].count - a[1].count ||
      a[0].localeCompare(b[0], 'fa'))
    .slice(0, Math.max(0, Math.min(8, maxColumns)))
    .map(([key]) => key)

  return {
    columns: keys.map((key, index) => ({ key: `spec_${index}`, label: key })),
    valuesByProduct: byProduct.map((values) =>
      Object.fromEntries(keys.map((key, index) => [`spec_${index}`, values.get(key) ?? 'نامشخص']))),
  }
}
