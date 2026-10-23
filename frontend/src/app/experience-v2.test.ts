import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const markup = readFileSync(new URL('../../index.html', import.meta.url), 'utf8')
const styles = readFileSync(new URL('../minimal-v3.css', import.meta.url), 'utf8')
const app = readFileSync(new URL('./App.tsx', import.meta.url), 'utf8')
const mission = readFileSync(new URL('../features/missions/MissionPanel.tsx', import.meta.url), 'utf8')
const entry = readFileSync(new URL('../main.tsx', import.meta.url), 'utf8')

describe('minimal Persian shopping experience v3', () => {
  it('uses native RTL and a readable Persian font', () => {
    expect(markup).toContain('lang="fa" dir="rtl"')
    expect(markup).toContain('Vazirmatn')
    expect(styles).toContain('font-family: "Vazirmatn"')
  })

  it('loads one concise visual layer and removes the redundant dashboard guide', () => {
    expect(entry).toContain("import './minimal-v3.css'")
    expect(entry).not.toContain("import './experience-v2.css'")
    expect(entry).not.toContain("import './torob-red.css'")
    expect(app).not.toContain('journey-sidebar')
    expect(app).not.toContain('journey-mobile-ribbon')
    expect(app).toContain('className="journey-workspace"')
  })

  it('preserves every existing user action and a keyboard-addressable composer', () => {
    expect(mission).toContain('onToggleOffers(result)')
    expect(mission).toContain('onToggleCompare(result)')
    expect(mission).toContain('onClick={handleLocationClick}')
    expect(mission).toContain('aria-expanded={Boolean(offerView?.expanded)}')
    expect(mission).toContain('id="conversation-composer"')
    expect(mission).toContain('id="conversation-heading"')
    expect(mission).toContain('aria-label="پیام به دستیار خرید"')
  })

  it('keeps seller and assistant explanations available on demand', () => {
    expect(mission).toContain('className="assistant-explanation"')
    expect(mission).toContain('className="mission-product-details"')
    expect(mission).toContain('className="conversation-disclosure"')
    expect(mission).toContain('نام بیشتر فروشگاه‌ها')
  })

  it('supports tablet, mobile, narrow devices, reduced motion and high contrast', () => {
    for (const width of [830, 550, 370]) {
      expect(styles).toContain(`@media (max-width: ${width}px)`)
    }
    expect(styles).toContain('prefers-reduced-motion: reduce')
    expect(styles).toContain('forced-colors: active')
    expect(styles).toContain('safe-area-inset-bottom')
    expect(styles).toContain(':focus-visible')
  })
})
