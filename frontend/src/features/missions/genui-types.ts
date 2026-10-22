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

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

/**
 * Parse the deliberately small server-to-client UI protocol. Unknown component types are
 * retained for a safe fallback renderer; arbitrary markup or executable code is never accepted.
 */
export function getUIComponents(event: MissionEvent): GenUIComponent[] {
  if (event.type !== 'ui.component') return []
  const type = typeof event.payload.component === 'string' ? event.payload.component : ''
  const data = isRecord(event.payload.data) ? event.payload.data : {}
  if (!type) return []

  if (type === 'component_stack' && Array.isArray(data.components)) {
    return data.components.flatMap((item, index) => {
      if (!isRecord(item) || typeof item.type !== 'string') return []
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
