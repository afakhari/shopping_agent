import type { CatalogOffer } from '../search/catalog-api'

export interface SellerHighlights { cheapestOfferId: string | null; closestOfferId: string | null }

/** Relative tags among only the already loaded and eligible seller offers.
 * Distances are straight-line distances, not routing/ETA estimates.
 */
export function sellerHighlights(offers: CatalogOffer[]): SellerHighlights {
  let cheapest: { id: string; price: bigint } | null = null
  let closest: { id: string; meters: number } | null = null
  for (const offer of offers) {
    if (offer.price_toman && /^\d+(?:\.0+)?$/.test(offer.price_toman)) {
      const price = BigInt(offer.price_toman.split('.')[0])
      if (!cheapest || price < cheapest.price) cheapest = { id: offer.id, price }
    }
    const distance = offer.shop.distance_m
    if (typeof distance === 'number' && Number.isFinite(distance) && distance >= 0) {
      if (!closest || distance < closest.meters) closest = { id: offer.id, meters: distance }
    }
  }
  return { cheapestOfferId: cheapest?.id ?? null, closestOfferId: closest?.id ?? null }
}
