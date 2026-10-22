import type { CatalogProduct } from '../search/catalog-api'

export interface ProductHighlight {
  key: string
  value: string
}

const IMPORTANT_SPECS: Array<{match: RegExp; patterns: RegExp[]}> = [
  { match: /لپ\s*تاپ|نوت\s*بوک|کامپیوتر/, patterns: [/پردازنده|cpu|processor/i, /رم|ram|حافظه اجرایی/i, /گرافیک|gpu/i, /وزن/i] },
  { match: /گوشی|موبایل|تلفن همراه/, patterns: [/حافظه داخلی|storage/i, /رم|ram/i, /باتری/i, /دوربین/i] },
  { match: /هدفون|هندزفری|ایرباد|هدست/, patterns: [/نویز|حذف صدا|anc/i, /باتری|شارژ|پخش/i, /اتصال|بلوتوث/i, /ضد آب|مقاومت/i] },
  { match: /تلویزیون|نمایشگر|مانیتور/, patterns: [/اندازه|سایز|اینچ/i, /رزولوشن|وضوح|4k/i, /پنل|نرخ نوسازی|رفرش/i] },
  { match: /یخچال|فریزر|ماشین لباسشویی/, patterns: [/ظرفیت|گنجایش/i, /مصرف انرژی|رده انرژی/i, /ابعاد/i] },
  { match: /فشارسنج|تجهیزات پزشکی/, patterns: [/نوع دستگاه|نوع کاربری/i, /دقت/i, /حافظه/i] },
]

const EXCLUDED_KEYS = /^(?:نام محصول|عنوان محصول|کد محصول|شناسه کالا|بارکد|sku|مدل|برند|گارانتی)$/i

/** Only show genuinely recorded catalog specifications. A missing field stays missing. */
export function chooseProductHighlights(product: CatalogProduct, max = 2): ProductHighlight[] {
  const seen = new Set<string>()
  const specs = (product.specs ?? []).flatMap((item) => {
    const key = typeof item.key === 'string' ? item.key.trim() : ''
    const value = typeof item.value === 'string' ? item.value.trim() : ''
    if (!key || !value || key.length > 45 || value.length > 90 ||
      EXCLUDED_KEYS.test(key) || /^(?:نامشخص|نامعلوم|[-—])$/.test(value)) return []
    const normalized = key.toLocaleLowerCase('fa')
    if (seen.has(normalized)) return []
    seen.add(normalized)
    return [{key, value}]
  })
  const category = `${product.category ?? ''} ${product.title ?? ''}`
  const patterns = IMPORTANT_SPECS.find((entry) => entry.match.test(category))?.patterns ?? []
  const score = (spec: ProductHighlight) => {
    const index = patterns.findIndex((pattern) => pattern.test(spec.key))
    return index < 0 ? patterns.length + 1 : index
  }
  return specs
    .map((spec, index) => ({...spec, rank: score(spec), index}))
    .sort((a,b) => a.rank - b.rank || a.index - b.index)
    .slice(0, Math.max(0, Math.min(3, max)))
    .map(({key,value}) => ({key,value}))
}
