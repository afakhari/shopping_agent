import { describe, expect, it } from 'vitest'
import { getUIComponents, getResultPayload } from './genui-types'
import type { MissionEvent } from './mission-api'

function event(component: string, data: Record<string, unknown>): MissionEvent {
  return {
    schema_version: 1,
    mission_id: 'test-mission',
    seq: 1,
    type: 'ui.component',
    payload: { component, data },
  }
}

describe('controlled Generative UI protocol', () => {
  it('normalizes a single server component', () => {
    const components = getUIComponents(event('clarification_form', { title: 'شروع', fields: [] }))
    expect(components).toHaveLength(1)
    expect(components[0]?.type).toBe('clarification_form')
    expect(components[0]?.data.title).toBe('شروع')
  })

  it('unwraps only valid components from a component stack', () => {
    const components = getUIComponents(event('component_stack', {
      components: [
        { type: 'category_choice', data: { alternative_query: 'فشارسنج صنعتی' } },
        { type: 'product_results', data: { query: 'فشارسنج', total: 2, results: [] } },
        { type: '<script>', data: 'not-an-object' },
        { data: {} },
      ],
    }))
    expect(components.map((component) => component.type)).toEqual(['category_choice', 'product_results', '<script>'])
    expect(getResultPayload(components)).toMatchObject({ query: 'فشارسنج', total: 2 })
  })

  it('ignores malformed event envelopes and non-UI events', () => {
    const notUI = { ...event('notice', {}), type: 'assistant.message' } as MissionEvent
    expect(getUIComponents(notUI)).toEqual([])
    expect(getUIComponents(event('', {}))).toEqual([])
  })
})
