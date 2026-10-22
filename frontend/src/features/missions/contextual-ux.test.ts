import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const app = readFileSync(new URL('../../app/App.tsx', import.meta.url), 'utf8')
const mission = readFileSync(new URL('./MissionPanel.tsx', import.meta.url), 'utf8')
const styles = readFileSync(new URL('../../minimal-v3.css', import.meta.url), 'utf8')

describe('progressive shopping surface', () => {
  it('avoids a second permanent brand header and shows connection trouble only when needed', () => {
    expect(app).not.toContain('<header className="chat-topbar">')
    expect(app).toContain('serviceUnavailable &&')
    expect(mission).toContain('دستیار خرید حضوری')
  })
  it('opens local filters as a dismissible native modal instead of inserting them among messages', () => {
    expect(mission).toContain('setActiveFilterForm({')
    expect(mission).toContain('<dialog ref={filterDialogRef}')
    expect(mission).toContain('dialog.showModal()')
    expect(mission).not.toContain('appendLocalComponent(current,')
    expect(styles).toContain('.mission-filter-dialog::backdrop')
  })
  it('leaves the last product results actionable after informational turns and respects manual scrolling', () => {
    expect(mission).toContain('currentResultsMessage?.id === item.id')
    expect(mission).toContain('allowActions={isCurrentResult}')
    expect(mission).toContain('shouldFollowConversation(')
    expect(mission).not.toContain('scrollIntoView(')
    expect(mission).toContain('if (!results.length) setLastQuery(displayQuery.trim())')
  })
})

describe('mobile viewport containment', () => {
  it('bounds the nested RTL flex/grid layout rather than cropping content', () => {
    expect(styles).toContain('Mobile overflow guard:')
    expect(styles).toContain('.redesign-v2 .journey-workspace,')
    expect(styles).toContain('.redesign-v2 .conversation-panel,')
    expect(styles).toContain('.redesign-v2 .conversation-welcome,')
    expect(styles).toContain('.redesign-v2 .conversation-composer,')
    expect(styles).toContain('min-inline-size: 0;')
    expect(styles).toContain('max-inline-size: 100%;')
    expect(styles).toContain('inline-size: calc(100% - 20px);')
    expect(styles).toContain('grid-template-columns: minmax(0, 1fr);')
  })
})
