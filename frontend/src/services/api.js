const API_BASE_URL = (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_BASE_URL) || 'http://127.0.0.1:5000'

const routeColors = {
  SAFE: '#2ec885',
  BALANCED: '#f4d35e',
  FUEL_SAVER: '#6ec8ff',
}

export const api = {
  async getRiskMap(forecastKey = 'current') {
    const response = await fetch(`${API_BASE_URL}/api/risk/heatmap?forecast=${encodeURIComponent(forecastKey)}`)
    if (!response.ok) {
      throw new Error(`Risk heatmap request failed: ${response.status}`)
    }

    const payload = await response.json()
    return {
      forecastKey,
      cells: Array.isArray(payload.cells) ? payload.cells : [],
      source: payload.source ?? 'backend',
    }
  },

  async calculateRoutes(start, destination) {
    if (!start || !destination) {
      return { routes: [] }
    }

    const response = await fetch(`${API_BASE_URL}/api/navigation/recommend`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        start: { latitude: start.lat, longitude: start.lng },
        destination: { latitude: destination.lat, longitude: destination.lng },
        vessel: { speed_knots: 12 },
        navigation_mode: 'BALANCED',
      }),
    })

    if (!response.ok) {
      throw new Error(`Route recommendation request failed: ${response.status}`)
    }

    const payload = await response.json()
    const recommendation = payload.recommendation ?? {}
    const routes = Array.isArray(recommendation.route) && recommendation.route.length > 0
      ? [{
          mode: recommendation.mode ?? 'BALANCED',
          name: recommendation.mode ?? 'BALANCED',
          color: routeColors[recommendation.mode ?? 'BALANCED'] ?? '#f4d35e',
          route_points: recommendation.route.map((point) => ({
            latitude: point.latitude,
            longitude: point.longitude,
            arrival_time_utc: point.arrival_time_utc,
            risk_level: point.risk_level,
            risk_score: point.risk_score,
            eta_hours: point.eta_hours,
          })),
          distance_km: recommendation.distance_km ?? 0,
          eta_hours: recommendation.eta_hours ?? 0,
          risk_score: recommendation.risk_score ?? 0,
          fuel_estimate: recommendation.fuel_estimate ?? 0,
          cost_score: recommendation.cost_score ?? 0,
        }]
      : []

    return {
      source: 'backend',
      routes,
    }
  },
}
