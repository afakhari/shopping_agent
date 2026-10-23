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
  | { type: 'open_region_picker' }
  | { type: 'verify_offer'; offerId: string; shopId: string }
  | { type: 'verify_selected_offer'; offerId: string; shopId: string }

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
  'seller_options',
  'seller_details',
  'contact_prompt',
  'location_choice',
])

const MAX_COMPONENTS_PER_EVENT = 12

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

/** Fail closed for seller cards; historical component types stay compatible. */
function isValidData(type: string, data: Record<string, unknown>): boolean {
  if (type === 'location_choice') {
    return data.city === 'tehran' && data.source_type === 'approximate_region'
  }
  if (type === 'comparison_table') {
    return data.source_type === 'registered_catalog'
      && Array.isArray(data.columns) && data.columns.length >= 2 && data.columns.length <= 16
      && data.columns.every((column) => isRecord(column) && typeof column.key === 'string'
        && typeof column.label === 'string')
      && Array.isArray(data.rows) && data.rows.length >= 2 && data.rows.length <= 3
      && data.rows.every((row) => isRecord(row)
        && typeof row.id === 'string' && typeof row.product === 'string')
      && data.availability_verified === false
  }
  if (type === 'contact_prompt') {
    return typeof data.offer_id === 'string' && data.offer_id.length > 0
      && typeof data.shop_id === 'string' && data.shop_id.length > 0
      && typeof data.product_id === 'string' && data.product_id.length > 0
      && data.source_type === 'demo_simulation'
  }
  if (type === 'seller_options') {
    return Array.isArray(data.offers) && data.offers.length <= 12
      && data.offers.every((offer) => isRecord(offer) && typeof offer.id === 'string'
        && isRecord(offer.shop) && typeof offer.shop.id === 'string')
  }
  if (type === 'seller_details') {
    return isRecord(data.offer) && typeof data.offer.id === 'string'
      && isRecord(data.offer.shop) && typeof data.offer.shop.id === 'string'
  }
  return true
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
      if (!isValidData(item.type, isRecord(item.data) ? item.data : {})) return []
      return [{
        type: item.type,
        data: isRecord(item.data) ? item.data : {},
        id: typeof item.id === 'string' ? item.id : `${event.seq}-${index}-${item.type}`,
      }]
    })
  }

  if (!isValidData(type, data)) return []
  return [{ type, data, id: `${event.seq}-${type}` }]
}

export function getResultPayload(components: GenUIComponent[]): unknown {
  return components.find((component) => component.type === 'product_results')?.data
}
