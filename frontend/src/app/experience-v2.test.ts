import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const markup = readFileSync(new URL('../../index.html', import.meta.url), 'utf8')
const styles = readFileSync(new URL('../experience-v2.css', import.meta.url), 'utf8')
const app = readFileSync(new URL('./App.tsx', import.meta.url), 'utf8')
const mission = readFileSync(new URL('../features/missions/MissionPanel.tsx', import.meta.url), 'utf8')
const entry = readFileSync(new URL('../main.tsx', import.meta.url), 'utf8')

describe('Persian-first shopping design contract', () => {
  it('sets a real right-to-left document with a readable Persian font', () => {
    expect(markup).toContain('lang="fa" dir="rtl"')
    expect(markup).toContain('Vazirmatn')
    expect(styles).toContain('font-family: "Vazirmatn"')
  })

  it('applies the visual layer last without removing existing interactive components', () => {
    expect(entry).toContain("import './experience-v2.css'")
    expect(entry.indexOf("import './experience-v2.css'")).toBeGreaterThan(entry.indexOf("import './visit-plan.css'"))
    expect(mission).toContain('onToggleOffers(result)')
    expect(mission).toContain('onToggleCompare(result)')
    expect(mission).toContain('onClick={handleLocationClick}')
    expect(mission).toContain('aria-expanded={Boolean(offerView?.expanded)}')
  })

  it('has distinct notebook, tablet, mobile and narrow phone layouts', () => {
    for (const width of [1150, 990, 720, 550, 385]) {
      expect(styles).toContain(`@media (max-width: ${width}px)`)
    }
    expect(styles).toContain('prefers-reduced-motion: reduce')
    expect(styles).toContain('forced-colors: active')
    expect(styles).toContain(':focus-visible')
    expect(styles).toContain('safe-area-inset-bottom')
  })

  it('uses meaningful informational landmarks and accessible form navigation', () => {
    expect(app).toContain('aria-labelledby="journey-steps-heading"')
    expect(app).toContain('href="#conversation-composer"')
    expect(mission).toContain('id="conversation-composer"')
    expect(mission).toContain('id="conversation-heading"')
    expect(mission).toContain('aria-label="پیام به دستیار خرید"')
  })

  it('does not market a simulated seller response as a verified live call', () => {
    expect(app).toContain('موجودی فروشگاه در این نسخه به‌صورت نمایشی بررسی می‌شود')
    expect(mission).toContain('قیمت ثبت‌شده، بدون ادعای موجودی قطعی')
  })
})
