import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const styles = readFileSync(new URL('../minimal-v3.css', import.meta.url), 'utf8')
const main = readFileSync(new URL('../main.tsx', import.meta.url), 'utf8')
const app = readFileSync(new URL('./App.tsx', import.meta.url), 'utf8')
const mission = readFileSync(new URL('../features/missions/MissionPanel.tsx', import.meta.url), 'utf8')
const brief = readFileSync(new URL('../../../docs/FINAL-DESIGN-TOROB-RED.fa.md', import.meta.url), 'utf8')

describe('Torob-inspired red palette without a cluttered page', () => {
  it('uses red for calls to action, green for positive status and white for reading', () => {
    expect(styles).toContain('--bc-primary: #d9273b;')
    expect(styles).toContain('--bc-success: #13774f;')
    expect(styles).toContain('background: #fff;')
    expect(styles).toContain('.mission-offers-toggle')
    expect(styles).toContain('.mission-credit-confirmed')
  })

  it('avoids decorative journey scaffolding but preserves shopping controls', () => {
    expect(app).not.toContain('<aside')
    expect(main).toContain("import './minimal-v3.css'")
    expect(mission).toContain('دیدن فروشگاه‌ها')
    expect(mission).toContain('مقایسه')
    expect(mission).toContain('تغییر شرایط')
  })

  it('never turns sparse shop data or simulated contacts into a real claim', () => {
    expect(mission).toContain('قیمت‌ها تاریخی‌اند')
    expect(mission).toContain('موجودی به‌صورت نمایشی بررسی می‌شود')
    expect(brief).toContain('شماره‌های تماس')
  })

  it('retains the competition goals in design documentation', () => {
    for (const stage of ['انتخاب محصول', 'پیداکردن فروشگاه', 'مقایسه فروشگاه‌ها', 'استعلام و برنامه مراجعه']) {
      expect(brief).toContain(stage)
    }
    expect(brief).toContain('۵ دقیقه')
  })
})
