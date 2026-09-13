import { mockRiskMap } from '../data/mockRiskData'
import { generateMockRoutes } from '../data/mockRoutes'

export const api = {
  async getRiskMap(forecastKey = 'current') {
    return {
      forecastKey,
      cells: mockRiskMap[forecastKey] ?? mockRiskMap.current,
      source: 'mock',
    }
  },

  async calculateRoutes(start, destination) {
    if (!start || !destination) {
      return { routes: [] }
    }

    return {
      source: 'mock',
      routes: generateMockRoutes(start, destination),
    }
  },
}
