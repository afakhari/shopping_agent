import type { CatalogOffer } from '../search/catalog-api'
import type { ContactAttemptResponse } from './mission-api'

export interface RecoveryChoice {
  kind: 'same_product' | 'replacement_model'
  offerId: string
  shopId: string
  shopName: string
  productTitle: string | null
  address: string | null
  priceToman: string | null
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null
}

function readable(value: unknown, max = 240): string | null {
  return typeof value === 'string' && value.trim() ? value.trim().slice(0, max) : null
}

function parseOffer(raw: unknown, kind: RecoveryChoice['kind'], productTitle: string | null): RecoveryChoice | null {
  const offer = asRecord(raw)
  const shop = asRecord(offer?.shop)
  const offerId = readable(offer?.id, 64)
  const shopId = readable(shop?.id, 64)
  if (!offerId || !shopId) return null

  const price = readable(offer?.price_toman, 35)
  return {
    kind,
    offerId,
    shopId,
    shopName: readable(shop?.name) ?? 'فروشگاه با نام نامشخص',
    productTitle,
    address: readable(shop?.address) ?? readable(shop?.location_label),
    priceToman: price && /^\d+(?:\.\d+)?$/.test(price) ? price : null,
  }
}

/** Bound the model-facing recovery UI to actual identifiers emitted by the backend. */
export function readRecoveryChoices(data: Record<string, unknown>): RecoveryChoice[] {
  const seen = new Set<string>()
  const choices: RecoveryChoice[] = []
  const append = (choice: RecoveryChoice | null) => {
    if (!choice || seen.has(choice.offerId)) return
    seen.add(choice.offerId)
    choices.push(choice)
  }

  if (Array.isArray(data.alternatives)) {
    for (const offer of data.alternatives.slice(0, 3)) append(parseOffer(offer, 'same_product', null))
  }
  if (Array.isArray(data.alternative_products)) {
    for (const candidate of data.alternative_products.slice(0, 3)) {
      const result = asRecord(candidate)
      const product = asRecord(result?.product)
      append(parseOffer(result?.best_offer, 'replacement_model', readable(product?.title, 400)))
    }
  }
  return choices
}

/** A click can only target a fallback previously returned for this browser's mission.
 * The Django endpoint repeats hard-filter checks before recording the attempt.
 */
export function resolveRecoveryOffer(
  responses: Record<string, ContactAttemptResponse>,
  offerId: string,
  shopId: string,
): CatalogOffer | null {
  for (const response of Object.values(responses)) {
    const alternateOffers: unknown[] = Array.isArray(response.alternatives)
      ? response.alternatives : []
    const models: unknown[] = Array.isArray(response.alternative_products)
      ? response.alternative_products : []
    for (const candidate of [...alternateOffers, ...models.map((item) => asRecord(item)?.best_offer)]) {
      const offer = asRecord(candidate)
      const shop = asRecord(offer?.shop)
      if (offer?.id === offerId && shop?.id === shopId) return candidate as CatalogOffer
    }
  }
  return null
}
