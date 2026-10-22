import { useState, type FormEvent, type ReactNode } from 'react'
import {
  AlertCircle,
  ArrowLeft,
  BadgeCheck,
  CheckCircle2,
  ClipboardList,
  HelpCircle,
  MapPin,
  SlidersHorizontal,
  Sparkles,
  Store,
} from 'lucide-react'
import type { GenUIAction, GenUIComponent, GenUIFormValues, GenUIValue } from './genui-types'
import { RecoveryOptions } from './RecoveryOptions'

interface GenUIDefaults {
  query: string
  max_price_toman: string
  must_have_in_person_credit: boolean
  sort: string
}

interface GenUIRendererProps {
  components: GenUIComponent[]
  defaults: GenUIDefaults
  disabled?: boolean
  onAction: (action: GenUIAction) => void
}

interface FormField {
  id: string
  label: string
  type: 'text' | 'number' | 'checkbox' | 'select' | 'radio'
  required?: boolean
  placeholder?: string
  helper_text?: string
  default_value?: string | number | boolean
  min?: number
  max?: number
  options?: Array<{ label: string; value: string }>
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

function text(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value : fallback
}

function normalizeNumericText(value: string): string {
  return value
    .replace(/[۰-۹]/g, (digit) => String('۰۱۲۳۴۵۶۷۸۹'.indexOf(digit)))
    .replace(/[٠-٩]/g, (digit) => String('٠١٢٣٤٥٦٧٨٩'.indexOf(digit)))
    .replace(/[٬،,\s]/g, '')
}

function readFields(value: unknown): FormField[] {
  if (!Array.isArray(value)) return []
  return value.flatMap((candidate) => {
    if (!isRecord(candidate) || typeof candidate.id !== 'string' || typeof candidate.label !== 'string') return []
    const type = candidate.type
    if (!['text', 'number', 'checkbox', 'select', 'radio'].includes(String(type))) return []
    const options = Array.isArray(candidate.options)
      ? candidate.options.flatMap((option) => {
          if (!isRecord(option) || typeof option.label !== 'string' || typeof option.value !== 'string') return []
          return [{ label: option.label, value: option.value }]
        })
      : undefined
    return [{
      id: candidate.id,
      label: candidate.label,
      type: type as FormField['type'],
      required: candidate.required === true,
      placeholder: text(candidate.placeholder),
      helper_text: text(candidate.helper_text),
      ...(typeof candidate.default_value === 'string' || typeof candidate.default_value === 'number' || typeof candidate.default_value === 'boolean'
        ? { default_value: candidate.default_value }
        : {}),
      ...(typeof candidate.min === 'number' ? { min: candidate.min } : {}),
      ...(typeof candidate.max === 'number' ? { max: candidate.max } : {}),
      ...(options ? { options } : {}),
    }]
  })
}

function initialValue(field: FormField, defaults: GenUIDefaults, data: Record<string, unknown>): GenUIValue {
  if (field.id === 'product_query' || field.id === 'query') return text(field.default_value, defaults.query || text(data.query))
  if (field.id === 'max_price_toman' || field.id === 'budget') {
    return field.default_value !== undefined ? String(field.default_value) : defaults.max_price_toman
  }
  if (field.id === 'must_have_in_person_credit') {
    return typeof field.default_value === 'boolean' ? field.default_value : defaults.must_have_in_person_credit
  }
  if (field.id === 'sort') return text(field.default_value, defaults.sort)
  if (field.default_value !== undefined) return field.default_value
  return field.type === 'checkbox' ? false : ''
}

function SchemaForm({
  component,
  defaults,
  onAction,
  disabled = false,
}: {
  component: GenUIComponent
  defaults: GenUIDefaults
  disabled?: boolean
  onAction: (action: GenUIAction) => void
}) {
  const data = component.data
  const fields = readFields(data.fields)
  const [values, setValues] = useState<GenUIFormValues>(() => Object.fromEntries(
    fields.map((field) => [field.id, initialValue(field, defaults, data)]),
  ))
  const [formError, setFormError] = useState<string | null>(null)
  if (!fields.length) return null

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    for (const field of fields) {
      const rawValue = values[field.id]
      const rawText = rawValue === undefined || rawValue === null ? '' : String(rawValue).trim()
      if (field.required && (field.type === 'checkbox' ? rawValue !== true : rawText.length === 0)) {
        setFormError(field.type === 'checkbox'
          ? `برای ادامه، «${field.label}» را تأیید کن.`
          : `واردکردن «${field.label}» الزامی است.`)
        return
      }
      if (field.type !== 'number' || !rawText) continue
      const normalized = normalizeNumericText(rawText)
      if (!/^\d+$/.test(normalized)) {
        setFormError(`برای «${field.label}» فقط عدد صحیح وارد کن؛ ارقام فارسی و انگلیسی هر دو پذیرفته می‌شوند.`)
        return
      }
      const numericValue = BigInt(normalized)
      if (field.min !== undefined && numericValue < BigInt(Math.trunc(field.min))) {
        setFormError(`مقدار «${field.label}» نباید کمتر از ${new Intl.NumberFormat('fa-IR').format(field.min)} باشد.`)
        return
      }
      if (field.max !== undefined && numericValue > BigInt(Math.trunc(field.max))) {
        setFormError(`مقدار «${field.label}» نباید بیشتر از ${new Intl.NumberFormat('fa-IR').format(field.max)} باشد.`)
        return
      }
    }
    setFormError(null)
    onAction({ type: 'submit_form', values, purpose: text(data.purpose, component.type) })
  }

  const update = (field: FormField, value: GenUIValue) => {
    setValues((current) => ({ ...current, [field.id]: value }))
    setFormError(null)
  }
  return (
    <form className="genui-form" noValidate onSubmit={submit}>
      {text(data.title) && <div className="genui-card-heading"><span className="genui-icon"><SlidersHorizontal size={17} /></span><div><h4>{text(data.title)}</h4>{text(data.description) && <p>{text(data.description)}</p>}</div></div>}
      <div className="genui-form-grid">
        {fields.map((field) => (
          <div className={`genui-field ${field.type === 'checkbox' ? 'checkbox-field' : ''}`} key={field.id}>
            {field.type === 'checkbox' ? (
              <label className="genui-checkbox-label">
                <input
                  type="checkbox"
                  disabled={disabled}
                  checked={Boolean(values[field.id])}
                  aria-describedby={field.helper_text ? `genui-${component.id ?? component.type}-${field.id}-help` : undefined}
                  onChange={(event) => update(field, event.target.checked)}
                />
                <span>{field.label}</span>
              </label>
            ) : (
              <>
                {field.type === 'radio' ? (
                  <fieldset
                    className="genui-radio-fieldset"
                    disabled={disabled}
                    aria-describedby={field.helper_text ? `genui-${component.id ?? component.type}-${field.id}-help` : undefined}
                  >
                    <legend>{field.label}{field.required && <span className="genui-required"> *</span>}</legend>
                    <div className="genui-radio-options">
                      {(field.options ?? []).map((option) => (
                        <label className={`genui-radio-option ${String(values[field.id] ?? '') === option.value ? 'selected' : ''}`} key={option.value}>
                          <input
                            type="radio"
                            name={`genui-${component.id ?? component.type}-${field.id}`}
                            value={option.value}
                            required={field.required}
                            checked={String(values[field.id] ?? '') === option.value}
                            onChange={() => update(field, option.value)}
                          />
                          <span className="genui-radio-indicator" aria-hidden="true" />
                          <span className="genui-radio-copy">{option.label}</span>
                        </label>
                      ))}
                    </div>
                  </fieldset>
                ) : (
                  <>
                    <label htmlFor={`genui-${component.id ?? component.type}-${field.id}`}>{field.label}{field.required && <span className="genui-required"> *</span>}</label>
                    {field.type === 'select' ? (
                      <select
                        id={`genui-${component.id ?? component.type}-${field.id}`}
                        value={String(values[field.id] ?? '')}
                        required={field.required}
                        disabled={disabled}
                        onChange={(event) => update(field, event.target.value)}
                      >
                        {!field.required && <option value="">فرقی ندارد</option>}
                        {(field.options ?? []).map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
                      </select>
                    ) : (
                      <input
                        id={`genui-${component.id ?? component.type}-${field.id}`}
                        type="text"
                        inputMode={field.type === 'number' ? 'numeric' : 'text'}
                        autoComplete={field.type === 'number' ? 'off' : 'on'}
                        dir={field.type === 'number' ? 'ltr' : 'rtl'}
                        className={field.type === 'number' ? 'genui-numeric-input' : undefined}
                        value={String(values[field.id] ?? '')}
                        required={field.required}
                        disabled={disabled}
                        aria-describedby={field.helper_text ? `genui-${component.id ?? component.type}-${field.id}-help` : undefined}
                        placeholder={field.placeholder}
                        onChange={(event) => update(field, event.target.value)}
                      />
                    )}
                  </>
                )}
              </>
            )}
            {field.helper_text && <small id={`genui-${component.id ?? component.type}-${field.id}-help`}>{field.helper_text}</small>}
          </div>
        ))}
      </div>
      {formError && <p className="genui-form-error" role="alert">{formError}</p>}
      <button className="genui-primary-action" type="submit" disabled={disabled}>{text(data.submit_label, component.type === 'clarification_form' ? 'ادامه با این اطلاعات' : 'اعمال شرایط')} <ArrowLeft size={15} /></button>
    </form>
  )
}

function CategoryChoice({ component, onAction, disabled }: { component: GenUIComponent; onAction: (action: GenUIAction) => void; disabled?: boolean }) {
  const data = component.data
  const label = text(data.label, 'تغییر حوزه جست‌وجو')
  const alternativeLabel = text(data.alternative_label)
  const alternativeQuery = text(data.alternative_query)
  return (
    <section className="genui-category-choice" aria-label="پیشنهاد حوزه جست‌وجو">
      <div className="genui-choice-copy"><Sparkles size={18} /><div><strong>{label}</strong><p>{text(data.message, 'برای دقیق‌تر شدن نتایج می‌توانی حوزه جست‌وجو را تغییر بدهی.')}</p></div></div>
      {alternativeLabel && alternativeQuery && <button type="button" disabled={disabled} onClick={() => onAction({ type: 'run_query', query: alternativeQuery })}>{alternativeLabel}<ArrowLeft size={15} /></button>}
    </section>
  )
}

function EmptyState({ component, defaults, onAction, disabled }: { component: GenUIComponent; defaults: GenUIDefaults; onAction: (action: GenUIAction) => void; disabled?: boolean }) {
  const data = component.data
  return (
    <section className="genui-empty-state">
      <div className="genui-empty-heading"><AlertCircle size={21} /><div><strong>{text(data.title, 'با این شرایط موردی پیدا نشد')}</strong><p>{text(data.message, 'شروط سخت خرید خودکار تغییر نمی‌کنند. می‌توانی عبارت یا فیلترها را اصلاح کنی.')}</p></div></div>
      {readFields(data.fields).length > 0 && <SchemaForm key={component.id ?? 'empty-state-form'} component={{ ...component, type: 'constraint_form' }} defaults={defaults} disabled={disabled} onAction={onAction} />}
      {readFields(data.fields).length === 0 && <button type="button" disabled={disabled} className="genui-secondary-action" onClick={() => onAction({ type: 'fill_query', query: text(data.query, defaults.query) })}>اصلاح عبارت جست‌وجو <ArrowLeft size={15} /></button>}
    </section>
  )
}

function ComparisonTable({ component }: { component: GenUIComponent }) {
  const columns = Array.isArray(component.data.columns) ? component.data.columns.filter(isRecord) : []
  const rows = Array.isArray(component.data.rows) ? component.data.rows.filter(isRecord) : []
  if (!columns.length || !rows.length) return <FallbackCard component={component} />
  return (
    <section className="genui-structured-card">
      <div className="genui-card-heading"><span className="genui-icon"><Store size={17} /></span><div><h4>{text(component.data.title, 'مقایسه گزینه‌ها')}</h4>{text(component.data.description) && <p>{text(component.data.description)}</p>}</div></div>
      <div className="genui-table-wrap"><table className="genui-table"><thead><tr>{columns.map((column, index) => <th key={String(column.key ?? index)}>{text(column.label, 'مشخصه')}</th>)}</tr></thead><tbody>{rows.map((row, rowIndex) => <tr key={String(row.id ?? rowIndex)}>{columns.map((column, columnIndex) => {const key = text(column.key); const value = key ? row[key] : ''; return <td key={key || columnIndex}>{typeof value === 'string' || typeof value === 'number' ? String(value) : value === null ? 'ثبت نشده' : '—'}</td>})}</tr>)}</tbody></table></div>
    </section>
  )
}

function VisitPlan({ component }: { component: GenUIComponent }) {
  const details = Array.isArray(component.data.details) ? component.data.details.filter(isRecord) : []
  const rawLocation = text(component.data.navigation_url)
  let safeLocation: string | null = null
  try {
    const parsed = new URL(rawLocation)
    if (parsed.protocol === 'https:' && parsed.hostname === 'www.openstreetmap.org') {
      safeLocation = parsed.toString()
    }
  } catch {
    // Ignore missing or invalid map URLs.
  }
  const backup = isRecord(component.data.backup_seller) ? component.data.backup_seller : null
  return (
    <section className="genui-visit-plan">
      <div className="genui-card-heading"><span className="genui-icon"><MapPin size={17} /></span><div><h4>{text(component.data.title, 'برنامه مراجعه')}</h4><p>{text(component.data.description, 'پیش از حرکت، اطلاعات زیر را مرور کن.')}</p></div></div>
      {text(component.data.status) && <span className="genui-status-chip"><BadgeCheck size={14} />{text(component.data.status)}</span>}
      {text(component.data.source_label) && <p className="genui-data-caveat">{text(component.data.source_label)}</p>}
      <dl>{details.map((detail, index) => {
        let value = text(detail.value, 'ثبت نشده')
        if (detail.key === 'last_price_changed_at' && value && value !== 'زمان تغییر قیمت ثبت نشده') {
          const date = new Date(value)
          if (!Number.isNaN(date.getTime())) value = new Intl.DateTimeFormat('fa-IR', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'Asia/Tehran' }).format(date)
        }
        return <div key={String(detail.key ?? index)}><dt>{text(detail.label, 'اطلاعات')}</dt><dd>{value}</dd></div>
      })}</dl>
      <section className="genui-visit-backup" aria-label="فروشنده پشتیبان">
        <strong>فروشنده پشتیبان</strong>
        {backup ? (
          <div>
            <span>{text(backup.name, 'فروشگاه جایگزین')}</span>
            <small>{text(backup.address, 'نشانی ثبت نشده')}</small>
            <small>{text(backup.status, 'موجودی استعلام نشده')}</small>
          </div>
        ) : <small>در داده‌های تحت پوشش فروشنده پشتیبان واجد شرایط دیگری پیدا نشد.</small>}
      </section>
      {safeLocation && (
        <a className="genui-primary-action genui-visit-navigation" href={safeLocation} target="_blank" rel="noopener noreferrer">
          <MapPin size={16} /> نمایش موقعیت فروشگاه روی نقشه <ArrowLeft size={15} />
        </a>
      )}
      <p className="genui-data-caveat">قیمت فهرست‌شده، به‌تنهایی تأیید موجودی خارج از سناریوی دمو نیست.</p>
    </section>
  )
}

function ContactStatus({ component }: { component: GenUIComponent }) {
  const firstAttempt = Array.isArray(component.data.attempts) && isRecord(component.data.attempts[0])
    ? component.data.attempts[0]
    : null
  const status = text(component.data.status, text(firstAttempt?.outcome, 'pending'))
  const positive = status === 'confirmed_available'
  const fallbackCopy = { title: 'وضعیت استعلام', message: 'وضعیت بر اساس نتیجه ثبت‌شده نمایش داده می‌شود.' }
  const messages: Record<string, { title: string; message: string }> = {
    confirmed_available: { title: 'موجودی در سناریوی دمو تأیید شد', message: 'اطلاعات فروشگاه را پیش از مراجعه مرور کن؛ این نتیجه تماس واقعی نیست.' },
    unavailable: { title: 'کالا در سناریوی دمو ناموجود است', message: 'گزینه‌های جایگزین با حفظ شروط اصلی در ادامه نمایش داده می‌شوند.' },
    no_answer: { title: 'فروشگاه در سناریوی دمو پاسخ نداد', message: 'نتیجه به‌معنای ناموجود بودن کالا نیست؛ می‌توانی فروشگاه یا مدل دیگری را بررسی کنی.' },
    closed: { title: 'فروشگاه در سناریوی دمو بسته است', message: 'می‌توانی برای مراجعه در زمان دیگر برنامه‌ریزی کنی یا گزینه دیگری را ببینی.' },
    error: { title: 'استعلام در سناریوی دمو ناموفق بود', message: 'این خطا موجودی کالا را مشخص نمی‌کند؛ گزینه دیگری را بررسی کن.' },
    price_changed: { title: 'قیمت در سناریوی دمو تغییر کرده است', message: 'مبلغ جدید مشخص نیست؛ برای حفظ سقف بودجه باید آفر جایگزین را بررسی کنی.' },
    pending: fallbackCopy,
  }
  const copy = messages[status] ?? fallbackCopy
  const evidence = isRecord(firstAttempt?.evidence) ? firstAttempt.evidence : null
  const stockEvidence = evidence && isRecord(evidence.stock) ? evidence.stock : null
  const priceEvidence = evidence && isRecord(evidence.price) ? evidence.price : null
  const hoursEvidence = evidence && isRecord(evidence.hours) ? evidence.hours : null
  const registeredPrice = priceEvidence ? text(priceEvidence.registered_price_toman) : ''
  const registeredHours = hoursEvidence ? text(hoursEvidence.weekly_hours) : ''
  return (
    <section className={`genui-contact-status ${positive ? 'positive' : 'caution'}`}>
      {positive ? <CheckCircle2 size={20} /> : <HelpCircle size={20} />}
      <div>
        <strong>{text(component.data.title, copy.title)}</strong>
        <p>{text(component.data.message, copy.message)}</p>
        {(stockEvidence || priceEvidence || hoursEvidence) && (
          <details className="genui-contact-evidence">
            <summary>جزئیات شواهد استعلام</summary>
            <div>
              {stockEvidence && <small>موجودی: {copy.title} (فقط سناریوی دمو)</small>}
              {priceEvidence && <small>قیمت ثبت‌شده: {registeredPrice ? `${registeredPrice} تومان` : 'نامشخص'}؛ {text(priceEvidence.status) === 'simulated_change_amount_unknown' ? 'در دمو تغییر قیمت گزارش شده، مبلغ جدید نامشخص است' : 'قیمت لحظه‌ای تأیید نشده است'}</small>}
              {hoursEvidence && <small>ساعات ثبت‌شده: {registeredHours || 'نامشخص'}؛ بازبودن واقعی تأیید نشده است.</small>}
            </div>
          </details>
        )}
        <small>شبیه‌سازی کنترل‌شده؛ تماس واقعی ارسال نشده است.</small>
      </div>
    </section>
  )
}

function FallbackCard({ component }: { component: GenUIComponent }) {
  return <section className="genui-fallback-card"><HelpCircle size={18} /><div><strong>{text(component.data.title, 'اطلاعات تکمیلی')}</strong><p>{text(component.data.message, 'این بخش از رابط برای این نسخه هنوز نمایش اختصاصی ندارد.')}</p></div></section>
}

function renderComponent(component: GenUIComponent, defaults: GenUIDefaults, onAction: (action: GenUIAction) => void, disabled: boolean): ReactNode {
  switch (component.type) {
    case 'component_stack':
      return null
    case 'product_results':
      // Product cards already have a specialised renderer with compare/contact controls.
      return null
    case 'clarification_form':
    case 'filter_form':
    case 'constraint_form':
      return <SchemaForm key={component.id ?? component.type} component={component} defaults={defaults} disabled={disabled} onAction={onAction} />
    case 'category_choice':
      return <CategoryChoice key={component.id ?? component.type} component={component} disabled={disabled} onAction={onAction} />
    case 'empty_state':
      return <EmptyState key={component.id ?? component.type} component={component} defaults={defaults} disabled={disabled} onAction={onAction} />
    case 'comparison_table':
      return <ComparisonTable key={component.id ?? component.type} component={component} />
    case 'visit_plan':
      return <VisitPlan key={component.id ?? component.type} component={component} />
    case 'contact_progress':
    case 'contact_status':
      return <ContactStatus key={component.id ?? component.type} component={component} />
    case 'notice':
      return <section className="genui-notice"><ClipboardList size={17} /><span>{text(component.data.message, text(component.data.title))}</span></section>
    case 'alternative_options':
      return <RecoveryOptions key={component.id ?? component.type} component={component} onAction={onAction} disabled={disabled} />
    default:
      return <FallbackCard key={component.id ?? component.type} component={component} />
  }
}

export function GenUIRenderer({ components, defaults, disabled = false, onAction }: GenUIRendererProps) {
  if (!components.length) return null
  return <div className="genui-renderer">{components.map((component, index) => <div className="genui-component" key={component.id ?? `${component.type}-${index}`}>{renderComponent(component, defaults, onAction, disabled)}</div>)}</div>
}
