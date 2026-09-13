// MOCK navigation boundary only: this is a conservative frontend-only land/ocean proxy.
// It is intentionally simple and will be replaced later by the backend's real geographic land mask.
export const MOCK_ANTARCTIC_COASTLINE = [
  { minLon: -180, maxLon: -150, coastLat: -69.5 },
  { minLon: -150, maxLon: -120, coastLat: -68.2 },
  { minLon: -120, maxLon: -96, coastLat: -66.8 },
  { minLon: -96, maxLon: -70, coastLat: -64.4 },
  { minLon: -70, maxLon: -38, coastLat: -62.8 },
  { minLon: -38, maxLon: -10, coastLat: -63.8 },
  { minLon: -10, maxLon: 18, coastLat: -65.1 },
  { minLon: 18, maxLon: 42, coastLat: -64.4 },
  { minLon: 42, maxLon: 72, coastLat: -62.2 },
  { minLon: 72, maxLon: 106, coastLat: -61.4 },
  { minLon: 106, maxLon: 142, coastLat: -64.1 },
  { minLon: 142, maxLon: 180, coastLat: -68.4 },
]

export function normalizeLongitude(longitude) {
  let normalized = longitude

  while (normalized > 180) normalized -= 360
  while (normalized < -180) normalized += 360

  return normalized
}

export function getMockCoastlineLatitude(longitude) {
  const normalized = normalizeLongitude(longitude)

  for (const segment of MOCK_ANTARCTIC_COASTLINE) {
    if (normalized >= segment.minLon && normalized <= segment.maxLon) {
      return segment.coastLat
    }
  }

  return -61.5
}
