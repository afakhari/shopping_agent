/** Broad dataset bounds, not a geocoding or route-eligibility guarantee. */
export function isTehranCatalogPoint(lat: number | null, lon: number | null): boolean {
  return typeof lat === 'number' && Number.isFinite(lat)
    && typeof lon === 'number' && Number.isFinite(lon)
    && lat >= 35.35 && lat <= 35.95 && lon >= 50.9 && lon <= 51.85
}

/** Official Neshan deeplink to a *registered point*, not a verified shop identity.
 * The URL is generated only from bounded Tehran coordinates. Nothing is sent
 * until the user clicks the external link.
 */
export function neshanPointUrl(lat: number | null, lon: number | null): string | null {
  if (!isTehranCatalogPoint(lat, lon)) return null
  const params = new URLSearchParams({ lat: String(lat), lng: String(lon) })
  return `https://nshn.ir/?${params.toString()}`
}

/** Official public Neshan navigation deeplink; NOT a provider ETA API.
 * Both endpoints are coordinates, never merchant names (which may be synthetic).
 */
export function neshanDrivingUrl(
  origin: { lat: number; lon: number } | null | undefined,
  destination: { lat: number | null; lon: number | null },
): string | null {
  if (!origin || !isTehranCatalogPoint(origin.lat, origin.lon)
    || !isTehranCatalogPoint(destination.lat, destination.lon)) return null
  const params = new URLSearchParams({
    origin: `${origin.lat},${origin.lon}`,
    destination: `${destination.lat},${destination.lon}`,
    vehicle: 'd',
  })
  return `https://nshn.ir/?${params.toString()}`
}

/** Map-only fallback: opening this optional iframe sends its location to OpenStreetMap.
 * No ETA, indoor navigation or real-time shop availability is implied.
 */
export function osmEmbedUrl(lat: number | null, lon: number | null): string | null {
  if (lat === null || lon === null || !Number.isFinite(lat) || !Number.isFinite(lon)) return null
  if (lat < -90 || lat > 90 || lon < -180 || lon > 180) return null
  const delta = 0.009
  const bounds = [lon - delta, lat - delta, lon + delta, lat + delta]
  const params = new URLSearchParams({
    bbox: bounds.join(','),
    layer: 'mapnik',
    marker: `${lat},${lon}`,
  })
  return `https://www.openstreetmap.org/export/embed.html?${params.toString()}`
}

/** Representative coordinates: medians of shops with matching area text in the supplied CSV.
 * They are examples of catalog coverage, not precise neighborhood centroids.
 */
export const TEHRAN_REGION_SAMPLES = [
  { id: 'tajrish', label: 'تجریش', lat: 35.80591, lon: 51.43004 },
  { id: 'haft-tir', label: 'هفت‌تیر', lat: 35.71708, lon: 51.42682 },
  { id: 'jomhouri', label: 'جمهوری', lat: 35.69490, lon: 51.41152 },
  { id: 'ferdowsi', label: 'فردوسی', lat: 35.69213, lon: 51.42248 },
  { id: 'bazaar', label: 'بازار بزرگ', lat: 35.68809, lon: 51.42127 },
  { id: 'jannat', label: 'جنت‌آباد', lat: 35.73823, lon: 51.30992 },
] as const
