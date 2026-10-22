import type { MissionEvent } from './mission-api'

export type GenUIValue = string | number | boolean
export type GenUIFormValues = Record<string, GenUIValue>

export interface GenUIComponent {
  type: string
  data: Record<string, unknown>
  id?: string
}

export type GenUIAction =
  | { type: 'submit_form'; values: GenUIFormValues; purpose: string }
  | { type: 'run_query'; query: string }
  | { type: 'fill_query'; query: string }
  | { type: 'open_filter_form' }
  | { type: 'verify_offer'; offerId: string; shopId: string }

/** A fixed vocabulary. The server/LLM can choose components, never execute arbitrary UI. */
const ALLOWED_COMPONENT_TYPES = new Set([
  'product_results',
  'clarification_form',
  'filter_form',
  'constraint_form',
  'category_choice',
  'empty_state',
  'comparison_table',
  'visit_plan',
  'contact_progress',
  'contact_status',
  'notice',
  'alternative_options',
])

const MAX_COMPONENTS_PER_EVENT = 12

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

/** Accept only registered components and a bounded one-level stack.
 * Unrecognized or malformed UI is ignored; the mission text/events still render normally.
 */
export function getUIComponents(event: MissionEvent): GenUIComponent[] {
  if (event.type !== 'ui.component') return []
  const type = typeof event.payload.component === 'string' ? event.payload.component : ''
  const data = isRecord(event.payload.data) ? event.payload.data : {}
  if (type !== 'component_stack' && !ALLOWED_COMPONENT_TYPES.has(type)) return []

  if (type === 'component_stack') {
    if (!Array.isArray(data.components)) return []
    return data.components.slice(0, MAX_COMPONENTS_PER_EVENT).flatMap((item, index) => {
      if (!isRecord(item) || typeof item.type !== 'string'
        || !ALLOWED_COMPONENT_TYPES.has(item.type)) return []
      return [{
        type: item.type,
        data: isRecord(item.data) ? item.data : {},
        id: typeof item.id === 'string' ? item.id : `${event.seq}-${index}-${item.type}`,
      }]
    })
  }

  return [{ type, data, id: `${event.seq}-${type}` }]
}

export function getResultPayload(components: GenUIComponent[]): unknown {
  return components.find((component) => component.type === 'product_results')?.data
}
