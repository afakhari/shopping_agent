import { describe, expect, it } from 'vitest'
import { currentRouteEvidence, routeEvidenceScope } from './routing-evidence'

const base = {
  missionId: 'mission-one',
  resultSetId: 'search-one',
  origin: {lat: 35.7, lon: 51.4},
  mode: 'car' as const,
  destinations: [{id: 'offer-1', shop: {lat: 35.701, lon: 51.401}}],
}

describe('Neshan ETA provenance', () => {
  it('keeps an ETA only for the exact active mission, result, origin and sellers', () => {
    const scope = routeEvidenceScope(base)
    const evidence = {scope, data: {duration_seconds: 300}}
    expect(currentRouteEvidence(evidence, scope, false)).toBe(evidence)
    expect(currentRouteEvidence(evidence, scope, true)).toBeNull()
    expect(currentRouteEvidence(evidence, routeEvidenceScope({...base, resultSetId: 'new-search'}), false)).toBeNull()
    expect(currentRouteEvidence(evidence, routeEvidenceScope({...base, origin: {lat: 35.75, lon: 51.4}}), false)).toBeNull()
    expect(currentRouteEvidence(evidence, routeEvidenceScope({...base, mode: 'motorcycle'}), false)).toBeNull()
    expect(currentRouteEvidence(evidence, routeEvidenceScope({...base, missionId: 'other-mission'}), false)).toBeNull()
    expect(currentRouteEvidence(evidence, routeEvidenceScope({...base, destinations: [
      {id: 'offer-2', shop: {lat: 35.703, lon: 51.41}},
    ]}), false)).toBeNull()
  })

  it('does not coerce missing route evidence into numbers', () => {
    expect(currentRouteEvidence(null, routeEvidenceScope(base), false)).toBeNull()
  })
})
