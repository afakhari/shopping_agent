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
    expect(components.map((component) => component.type)).toEqual(['category_choice', 'product_results'])
    expect(getResultPayload(components)).toMatchObject({ query: 'فشارسنج', total: 2 })
  })

  it('accepts known recovery UI from the backend', () => {
    expect(getUIComponents(event('alternative_options', { alternatives: [] }))[0]?.type)
      .toBe('alternative_options')
  })

  it('accepts grounded store cards and rejects invented/malformed store data', () => {
    const valid = event('seller_options', { offers: [
      { id: 'offer1', shop: { id: 'shop1', name: 'فروشگاه نمونه', address: 'تهران' } },
    ] })
    expect(getUIComponents(valid)).toHaveLength(1)
    expect(getUIComponents(event('seller_options', { offers: [{ title: 'جعلی' }] }))).toEqual([])
    expect(getUIComponents(event('seller_details', { offer: { id: 'o1' } }))).toEqual([])
    expect(getUIComponents(event('seller_options', {
      offers: Array.from({ length: 13 }, (_, index) => ({
        id: String(index), shop: { id: String(index) },
      })),
    }))).toEqual([])
  })

  it('requires server-issued source IDs and demo provenance for contact consent', () => {
    const valid = event('contact_prompt', {
      offer_id: 'offer1', shop_id: 'shop1', product_id: 'product1',
      source_type: 'demo_simulation',
    })
    expect(getUIComponents(valid)).toHaveLength(1)
    expect(getUIComponents(event('contact_prompt', {
      offer_id: 'offer1', shop_id: 'shop1', product_id: 'product1',
      source_type: 'live_verified',
    }))).toEqual([])
    expect(getUIComponents(event('contact_prompt', {
      shop_id: 'shop1', source_type: 'demo_simulation',
    }))).toEqual([])
  })

  it('limits one incoming component stack to twelve entries', () => {
    const components = getUIComponents(event('component_stack', {
      components: Array.from({ length: 30 }, () => ({ type: 'notice', data: { message: 'notice' } })),
    }))
    expect(components).toHaveLength(12)
  })

  it('ignores malformed event envelopes and non-UI events', () => {
    const notUI = { ...event('notice', {}), type: 'assistant.message' } as MissionEvent
    expect(getUIComponents(notUI)).toEqual([])
    expect(getUIComponents(event('', {}))).toEqual([])
    expect(getUIComponents(event('<script>', {}))).toEqual([])
    expect(getUIComponents(event('component_stack', {
      components: [{ type: 'component_stack', data: { components: [] } }],
    }))).toEqual([])
  })
})
