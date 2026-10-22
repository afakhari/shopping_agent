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

describe('evidence-first purchase flow', () => {
  it('presents editable filters and a user-controlled comparison tray', () => {
    expect(mission).toContain('<ActiveShoppingFilters')
    expect(mission).toContain('mission-compare-tray')
    expect(mission).toContain('setComparisonOpen(')
  })
  it('renders one explanatory heading for a missing result instead of three repeated warnings', () => {
    const genUI = readFileSync(new URL('./GenUIRenderer.tsx', import.meta.url), 'utf8')
    expect(mission).toContain("!item.components.some((component) => component.type === 'empty_state')")
    expect(genUI).toContain("data: { ...data, title: undefined, description: undefined }")
    expect(genUI).toContain('genui-empty-heading')
  })
  it('routes short help and greetings without starting a paid LLM request', () => {
    expect(mission).toContain('const localIntent = classifyLocalConversation(trimmed)')
    const localIntents = readFileSync(new URL('./greeting-intent.ts', import.meta.url), 'utf8')
    expect(localIntents).toContain('چطور ازت استفاده کنم')
  })
  it('never blindly reposts a failed turn or a failed contact request', () => {
    expect(mission).toContain('completedTurnWasPersisted(snapshot, trimmed, lastSavedSequence)')
    expect(mission).toContain('clientRequestId = pendingContactIdsRef.current.get(requestKey)')
    expect(mission).toContain('بازیابی وضعیت')
  })
  it('keeps seller details optional instead of expanding every long address', () => {
    expect(mission).toContain('<details className="mission-seller-details">')
    expect(styles).toContain('.mission-seller-details summary')
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
