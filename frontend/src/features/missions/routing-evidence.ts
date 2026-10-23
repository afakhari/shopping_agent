/** Scope provider estimates to the exact source evidence the buyer saw. */
export function routeEvidenceScope(args: {
  missionId: string
  resultSetId: string | null
  origin: { lat: number; lon: number } | null | undefined
  mode: 'car' | 'motorcycle'
  destinations: Array<{ id: string; shop: { lat: number | null; lon: number | null } }>
}): string {
  return JSON.stringify([
    args.missionId, args.resultSetId,
    args.origin?.lat ?? null, args.origin?.lon ?? null, args.mode,
    args.destinations.map(offer => [offer.id, offer.shop.lat, offer.shop.lon]),
  ])
}

/** An old ETA must never appear after an origin, seller, mode or result change. */
export function currentRouteEvidence<T extends { scope: string }>(
  evidence: T | null, scope: string, disabled: boolean,
): T | null {
  return !disabled && evidence?.scope === scope ? evidence : null
}
