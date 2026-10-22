import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const theme = readFileSync(new URL('../torob-red.css', import.meta.url), 'utf8')
const entry = readFileSync(new URL('../main.tsx', import.meta.url), 'utf8')
const challengeDocs = readFileSync(new URL('../../../docs/FINAL-DESIGN-TOROB-RED.fa.md', import.meta.url), 'utf8')

describe('Torob-inspired, Persian-first shopping theme', () => {
  it('is loaded after the established components and does not remove UX v2', () => {
    expect(entry).toContain("import './experience-v2.css'")
    expect(entry).toContain("import './torob-red.css'")
    expect(entry.indexOf("import './torob-red.css'")).toBeGreaterThan(
      entry.indexOf("import './experience-v2.css'"),
    )
  })

  it('gives red to actions and green exclusively to confirmed states', () => {
    expect(theme).toContain('--bc-primary: #df2638;')
    expect(theme).toContain('--bc-success: #16815c;')
    expect(theme).toContain('.mission-offers-toggle')
    expect(theme).toContain('.composer-send')
    expect(theme).toContain('.mission-credit-confirmed')
  })

  it('avoids a narrow fixed results column on desktops and covers mobile', () => {
    expect(theme).toContain('flex-direction: column;')
    expect(theme).toContain('.journey-steps ol')
    expect(theme).toContain('grid-template-columns: repeat(4, minmax(0, 1fr))')
    expect(theme).toContain('@media (max-width: 990px)')
    expect(theme).toContain('@media (max-width: 550px)')
    expect(theme).toContain('@media (prefers-reduced-motion: reduce)')
    expect(theme).toContain('@media (forced-colors: active)')
  })

  it('documents all four required steps and the synthetic store identities', () => {
    for (const stage of ['انتخاب محصول', 'پیداکردن فروشگاه', 'مقایسه فروشگاه‌ها', 'استعلام و برنامه مراجعه']) {
      expect(challengeDocs).toContain(stage)
    }
    expect(challengeDocs).toContain('۶۳۶۴')
    expect(challengeDocs).toContain('شماره‌های تماس')
    expect(challengeDocs).toContain('۵ دقیقه')
  })
})
