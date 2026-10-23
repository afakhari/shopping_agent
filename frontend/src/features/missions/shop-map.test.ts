import { describe, expect, it } from 'vitest'

import { isTehranCatalogPoint, neshanDrivingUrl, neshanPointUrl, osmEmbedUrl, TEHRAN_REGION_SAMPLES } from './shop-map'

describe('map fallback and manual area anchors', () => {
  it('accepts a real Tehran point and encodes a marker', () => {
    const url = osmEmbedUrl(35.7, 51.4)
    expect(url).toMatch(/^https:\/\/www\.openstreetmap\.org\/export\/embed\.html\?/)
    expect(new URL(url!).searchParams.get('marker')).toBe('35.7,51.4')
  })

  it('rejects missing and impossible coordinates without constructing a map request', () => {
    expect(osmEmbedUrl(null, 51.4)).toBeNull()
    expect(osmEmbedUrl(35.7, null)).toBeNull()
    expect(osmEmbedUrl(Number.NaN, 51.4)).toBeNull()
    expect(osmEmbedUrl(95, 51.4)).toBeNull()
    expect(osmEmbedUrl(35.7, 190)).toBeNull()
  })

  it('builds keyless Neshan links to registered points without a merchant name', () => {
    const point = neshanPointUrl(35.7, 51.4)
    expect(point).toBe('https://nshn.ir/?lat=35.7&lng=51.4')
    const url = neshanDrivingUrl({ lat: 35.69, lon: 51.41 }, { lat: 35.7, lon: 51.4 })
    expect(url).not.toBeNull()
    const parsed = new URL(url!)
    expect(parsed.origin).toBe('https://nshn.ir')
    expect(parsed.searchParams.get('origin')).toBe('35.69,51.41')
    expect(parsed.searchParams.get('destination')).toBe('35.7,51.4')
    expect(parsed.searchParams.get('vehicle')).toBe('d')
    expect(url).not.toContain('shop')
  })

  it('does not invent a route without an explicit valid Tehran origin and shop position', () => {
    const target = { lat: 35.7, lon: 51.4 }
    expect(neshanDrivingUrl(null, target)).toBeNull()
    expect(neshanDrivingUrl({lat: 52.5, lon: 13.4}, target)).toBeNull()
    expect(neshanDrivingUrl({lat: 35.69, lon: 51.41}, {lat: null, lon: 51.4})).toBeNull()
    expect(neshanPointUrl(52.5, 13.4)).toBeNull()
    expect(neshanPointUrl(null, 51.4)).toBeNull()
  })

  it('rejects off-dataset world positions without calling a geocoder', () => {
    expect(isTehranCatalogPoint(35.7, 51.4)).toBe(true)
    expect(isTehranCatalogPoint(52.52, 13.405)).toBe(false)
    expect(isTehranCatalogPoint(null, 51.4)).toBe(false)
    expect(isTehranCatalogPoint(35.7, Number.POSITIVE_INFINITY)).toBe(false)
  })

  it('keeps manual catalog samples within supported Tehran coordinates', () => {
    expect(TEHRAN_REGION_SAMPLES.length).toBeGreaterThanOrEqual(5)
    for (const area of TEHRAN_REGION_SAMPLES) {
      expect(area.lat).toBeGreaterThan(35.35)
      expect(area.lat).toBeLessThan(35.95)
      expect(area.lon).toBeGreaterThan(50.9)
      expect(area.lon).toBeLessThan(51.85)
    }
  })
})
