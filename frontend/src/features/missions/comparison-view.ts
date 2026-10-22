/** Turn the source-backed comparison matrix into a mobile-readable feature-first view. */
export interface ComparisonField {
  key: string
  label: string
  values: string[]
  different: boolean
}

export function buildComparisonFields(
  columns: Array<{key: string; label: string}>,
  products: Array<Record<string, string>>,
): ComparisonField[] {
  return columns
    .filter((column) => column.key !== 'product' && column.key.length > 0)
    .slice(0, 14)
    .map((column) => {
      const values = products.map((item) => {
        const raw = item[column.key]
        return typeof raw === 'string' && raw.trim() ? raw.trim() : 'ثبت نشده'
      })
      return {
        key: column.key,
        label: column.label,
        values,
        different: new Set(values.map((value) => value.normalize('NFKC').trim())).size > 1,
      }
    })
}

export function visibleComparisonFields(fields: ComparisonField[], onlyDifferences: boolean): ComparisonField[] {
  if (!onlyDifferences) return fields
  const alwaysVisible = new Set(['price', 'shop', 'credit'])
  return fields.filter((field) => field.different || alwaysVisible.has(field.key))
}
