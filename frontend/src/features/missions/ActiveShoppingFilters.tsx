import { MapPin, SlidersHorizontal } from 'lucide-react'
import type { MissionConstraints } from './mission-api'

const money = new Intl.NumberFormat('fa-IR', { maximumFractionDigits: 0 })
const sortLabels: Record<string, string> = {
  price_asc: 'ارزان‌ترین',
  distance_asc: 'نزدیک‌ترین (فاصله مستقیم)',
  recent_price_change: 'تازه‌ترین تغییر قیمت',
}

function budgetLabel(amount: string | null | undefined): string | null {
  if (!amount) return null
  try { return `تا ${money.format(BigInt(amount))} تومان` } catch { return null }
}

/** Overview opens the existing accessible filter dialog; it never removes hard constraints silently. */
export function ActiveShoppingFilters({
  constraints, onEdit, disabled,
}: {
  constraints: MissionConstraints
  onEdit: () => void
  disabled: boolean
}) {
  const entries = [
    budgetLabel(constraints.max_price_toman),
    constraints.must_have_in_person_credit ? 'خرید اعتباری حضوری' : null,
    typeof constraints.lat === 'number' && typeof constraints.lon === 'number'
      ? `تا ${money.format((constraints.radius_m ?? 3000)/1000)} کیلومتر از محدوده انتخاب‌شده` : null,
    constraints.sort && constraints.sort !== 'relevance' ? sortLabels[constraints.sort] : null,
  ].filter((label): label is string => Boolean(label))
  if (!entries.length) return null
  return (
    <div className="mission-active-filters" aria-label="شرایط فعال جست‌وجو">
      <strong><MapPin size={14} aria-hidden="true" /> شرایط همین جست‌وجو</strong>
      <div className="mission-active-filter-list">
        {entries.map((label) => (
          <button type="button" disabled={disabled} key={label} onClick={onEdit} title="ویرایش شرایط در فرم">
            {label} <SlidersHorizontal size={12} aria-hidden="true" />
          </button>
        ))}
      </div>
    </div>
  )
}
