/** Strict, source-grounded price display for API Decimal strings in whole tomans. */
const money = new Intl.NumberFormat('fa-IR', { maximumFractionDigits: 0 })
const WHOLE_TOMAN = /^\d+(?:\.0+)?$/

export function formatCatalogPrice(price: string | null | undefined): string {
  if (price === null || price === undefined || price === '') return 'قیمت ثبت نشده'
  if (!WHOLE_TOMAN.test(price)) return 'قیمت نامشخص'
  try {
    return `${money.format(BigInt(price.split('.')[0]!))} تومان`
  } catch {
    return 'قیمت نامشخص'
  }
}
