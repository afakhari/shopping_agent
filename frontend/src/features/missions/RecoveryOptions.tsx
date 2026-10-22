import { ArrowLeft, RotateCcw, ShieldCheck, Store } from 'lucide-react'
import type { GenUIAction, GenUIComponent } from './genui-types'
import { readRecoveryChoices, type RecoveryChoice } from './recovery-options'
import { formatCatalogPrice } from './catalog-pricing'

const toman = new Intl.NumberFormat('fa-IR', { maximumFractionDigits: 0 })

function displayPrice(price: string | null): string {
  return formatCatalogPrice(price)
}

function RecoveryRow({ choice, disabled, onAction }: {
  choice: RecoveryChoice
  disabled: boolean
  onAction: (action: GenUIAction) => void
}) {
  return (
    <li className="genui-recovery-row">
      <div className="genui-recovery-copy">
        <strong>{choice.productTitle ?? choice.shopName}</strong>
        {choice.productTitle && <span><Store size={13} aria-hidden="true" />{choice.shopName}</span>}
        <span className="genui-recovery-price">{displayPrice(choice.priceToman)}</span>
        {choice.address && <small>{choice.address}</small>}
        <small>آفر ثبت‌شده؛ موجودی واقعی تأیید نشده است.</small>
      </div>
      <button
        type="button"
        className="genui-recovery-action"
        disabled={disabled}
        aria-label={`اجرای استعلام شبیه‌سازی‌شده از ${choice.shopName}`}
        onClick={() => onAction({
          type: 'verify_offer',
          offerId: choice.offerId,
          shopId: choice.shopId,
        })}
      >
        <ShieldCheck size={15} aria-hidden="true" />
        بررسی شبیه‌سازی‌شده
        <ArrowLeft size={14} aria-hidden="true" />
      </button>
    </li>
  )
}

/** Recovery as an actionable tool result, not generic chatbot prose.
 * The user explicitly approves each new demo contact by clicking its control.
 */
export function RecoveryOptions({ component, onAction, disabled }: {
  component: GenUIComponent
  onAction: (action: GenUIAction) => void
  disabled: boolean
}) {
  const choices = readRecoveryChoices(component.data)
  const shops = choices.filter((choice) => choice.kind === 'same_product')
  const models = choices.filter((choice) => choice.kind === 'replacement_model')
  return (
    <section className="genui-recovery" aria-label="گزینه‌های بازیابی خرید">
      <header className="genui-recovery-header">
        <RotateCcw size={18} aria-hidden="true" />
        <div>
          <strong>راه‌های ادامه خرید</strong>
          <p>استعلام پیشین به نتیجه قطعی قابل مراجعه نرسید. گزینه‌های ثبت‌شده را با همان شروط بررسی کن.</p>
        </div>
      </header>
      {shops.length > 0 ? (
        <div className="genui-recovery-group">
          <h4>همین محصول از فروشگاه دیگر</h4>
          <ul>{shops.map((choice) => (
            <RecoveryRow key={choice.offerId} choice={choice} onAction={onAction} disabled={disabled} />
          ))}</ul>
        </div>
      ) : <p className="genui-recovery-empty">فروشگاه جایگزین همین محصول با شرایط فعلی پیدا نشد.</p>}
      {models.length > 0 && (
        <details className="genui-recovery-more">
          <summary>مدل‌های جایگزین ({toman.format(models.length)})</summary>
          <ul>{models.map((choice) => (
            <RecoveryRow key={choice.offerId} choice={choice} onAction={onAction} disabled={disabled} />
          ))}</ul>
        </details>
      )}
      <p className="genui-recovery-note">این بررسی صرفاً شبیه‌سازی مسابقه است؛ قیمت و موجودی لحظه‌ای فروشگاه تأیید نشده‌اند.</p>
    </section>
  )
}
