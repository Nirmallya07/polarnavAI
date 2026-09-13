import { getMockCoastlineLatitude } from './antarcticCoastline.js'

const ROUTE_PROFILES = {
  SAFE: {
    mode: 'SAFE',
    name: 'Safest',
    color: '#2ec885',
    corridorOffset: -2.5,
    corridorScale: 0.7,
    seaBias: 1.3,
    distance_km: 1842,
    eta_hours: 82,
    fuel_estimate: 1240,
    cost_score: 52,
    risk_score: 27,
  },
  BALANCED: {
    mode: 'BALANCED',
    name: 'Balanced',
    color: '#f4d35e',
    corridorOffset: 0,
    corridorScale: 1,
    seaBias: 0.9,
    distance_km: 1765,
    eta_hours: 78,
    fuel_estimate: 1180,
    cost_score: 68,
    risk_score: 41,
  },
  FUEL_SAVER: {
    mode: 'FUEL_SAVER',
    name: 'Fuel Efficient',
    color: '#6ec8ff',
    corridorOffset: 2.2,
    corridorScale: 1.25,
    seaBias: 0.5,
    distance_km: 1690,
    eta_hours: 75,
    fuel_estimate: 1090,
    cost_score: 81,
    risk_score: 57,
  },
}

function clampToSouthernOcean(lat, lon) {
  const minLatitude = -78.5
  const maxLatitude = -55
  const safeLatitude = Math.min(Math.max(lat, minLatitude), maxLatitude)

  return {
    latitude: Number(safeLatitude.toFixed(4)),
    longitude: Number(Number(lon).toFixed(4)),
  }
}

function smoothStep(t) {
  return t * t * (3 - 2 * t)
}

function buildOceanBoundaryAwareWaypoint(anchor, next, profile) {
  const coastLat = getMockCoastlineLatitude(next.longitude)
  const corridorTarget = coastLat + profile.corridorOffset + profile.corridorScale * (anchor.latitude - coastLat)
  const offshoreMargin = Math.max(1.2, Math.abs(next.longitude - anchor.longitude) * 0.12)
  const preferredLat = Math.min(anchor.latitude, corridorTarget) - offshoreMargin * profile.seaBias

  const boundedLat = Math.min(Math.max(preferredLat, -78.5), -56)

  return {
    latitude: boundedLat,
    longitude: next.longitude,
  }
}

function generateWaypoints(start, destination, profile) {
  const startLat = Number(start.lat)
  const startLon = Number(start.lng)
  const endLat = Number(destination.lat)
  const endLon = Number(destination.lng)

  const deltaLat = endLat - startLat
  const deltaLon = endLon - startLon
  const totalSegments = 18
  const basePoints = []

  for (let i = 0; i <= totalSegments; i += 1) {
    const t = i / totalSegments
    const eased = smoothStep(t)

    const baseLat = startLat + deltaLat * eased
    const baseLon = startLon + deltaLon * eased

    const coastLat = getMockCoastlineLatitude(baseLon)
    const corridorCenter = coastLat + profile.corridorOffset + (profile.corridorScale * 2.8)
    const lateralCurve = Math.sin((t * Math.PI) + profile.corridorOffset) * 4.5
    const verticalCurve = Math.cos((t * Math.PI * 1.6) + profile.seaBias) * 1.8

    let adjustedLat = baseLat + verticalCurve
    adjustedLat += (coastLat + 3.8 - adjustedLat) * 0.5
    adjustedLat += lateralCurve * (Math.abs(deltaLon) > 10 ? 0.35 : 0.22)

    if (adjustedLat < coastLat + 1.8) {
      adjustedLat = coastLat + 1.8 + Math.abs(Math.sin((t + 1) * 3.5)) * 2.2
    }

    const wayPoint = clampToSouthernOcean(adjustedLat, baseLon)
    basePoints.push({ latitude: wayPoint.latitude, longitude: wayPoint.longitude })
  }

  const smoothed = [basePoints[0]]
  for (let i = 1; i < basePoints.length - 1; i += 1) {
    const prev = basePoints[i - 1]
    const current = basePoints[i]
    const next = basePoints[i + 1]

    const midLat = (prev.latitude + current.latitude + next.latitude) / 3
    const midLon = (prev.longitude + current.longitude + next.longitude) / 3
    const boundaryOffset = (getMockCoastlineLatitude(midLon) + profile.corridorOffset) * 0.35
    const correctedLat = Math.max(midLat, boundaryOffset)

    smoothed.push({
      latitude: clampToSouthernOcean(correctedLat, midLon).latitude,
      longitude: Number(midLon.toFixed(4)),
    })
  }
  smoothed.push(basePoints[basePoints.length - 1])

  const anchored = smoothed.map((point, index) => {
    if (index === 0) return { latitude: startLat, longitude: startLon }
    if (index === smoothed.length - 1) return { latitude: endLat, longitude: endLon }

    const coastLat = getMockCoastlineLatitude(point.longitude)
    const safePoint = buildOceanBoundaryAwareWaypoint({ latitude: point.latitude, longitude: point.longitude }, { latitude: coastLat, longitude: point.longitude }, profile)
    return {
      latitude: safePoint.latitude,
      longitude: safePoint.longitude,
    }
  })

  return anchored
}

function finalizeRoutePoints(routePoints) {
  return routePoints.map((point, index) => {
    const latitude = Number(point.latitude.toFixed(4))
    const longitude = Number(point.longitude.toFixed(4))
    const riskScore = 18 + Math.round((index / Math.max(routePoints.length - 1, 1)) * 40)

    return {
      latitude,
      longitude,
      risk_level: 'LOW',
      risk_score: riskScore,
      eta_hours: Math.round(index * 4.5),
      arrival_time_utc: `2026-09-15T${String(Math.min(23, Math.round(index * 2))).padStart(2, '0')}:00:00Z`,
    }
  })
}

export function generateMockRoutes(start, destination) {
  if (!start || !destination) {
    return []
  }

  const profiles = Object.values(ROUTE_PROFILES)

  return profiles.map((profile) => ({
    ...profile,
    route_points: finalizeRoutePoints(generateWaypoints(start, destination, profile)),
  }))
}

export const mockRoutes = generateMockRoutes({ lat: -64, lng: 40 }, { lat: -70.5, lng: 18 })
