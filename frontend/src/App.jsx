import { useEffect, useMemo, useState } from 'react'
import { AntarcticMap } from './components/Map/AntarcticMap'
import { MapLegend } from './components/Map/MapLegend'
import { RouteComparison } from './components/Routes/RouteComparison'
import { ForecastSelector } from './components/Voyage/ForecastSelector'
import { VoyagePanel } from './components/Voyage/VoyagePanel'
import { api } from './services/api'
import { forecastOptions } from './data/mockRiskData'
import './App.css'

const defaultStart = { lat: -64.0, lng: 40.0 }
const defaultDestination = { lat: -70.5, lng: 18.0 }

function App() {
  const [selectedForecast, setSelectedForecast] = useState('plus3')
  const [selectionMode, setSelectionMode] = useState(null)
  const [startPoint, setStartPoint] = useState(defaultStart)
  const [destinationPoint, setDestinationPoint] = useState(defaultDestination)
  const [riskCells, setRiskCells] = useState([])
  const [routes, setRoutes] = useState([])
  const [selectedRoute, setSelectedRoute] = useState(null)

  useEffect(() => {
    const loadRisk = async () => {
      try {
        const data = await api.getRiskMap(selectedForecast)
        setRiskCells(data.cells)
      } catch (error) {
        console.error('Unable to load risk map from backend', error)
        setRiskCells([])
      }
    }

    loadRisk()
  }, [selectedForecast])

  const canCalculate = useMemo(
    () => Boolean(startPoint && destinationPoint),
    [startPoint, destinationPoint],
  )

  const handleMapClick = (latlng) => {
    if (!selectionMode) return

    const point = { lat: latlng.lat, lng: latlng.lng }

    if (selectionMode === 'start') {
      setStartPoint(point)
    }

    if (selectionMode === 'destination') {
      setDestinationPoint(point)
    }

    setSelectionMode(null)
  }

  const handleCalculateRoutes = async () => {
    if (!canCalculate) return

    const result = await api.calculateRoutes(startPoint, destinationPoint)
    if (result.routes?.length) {
      setRoutes(result.routes)
      setSelectedRoute(result.routes[0])
    }
  }

  const handleReset = () => {
    setStartPoint(null)
    setDestinationPoint(null)
    setRoutes([])
    setSelectedRoute(null)
    setSelectionMode(null)
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-block">
          <div className="brand-mark">P</div>
          <div>
            <div className="brand-title">PolarNav AI</div>
            <div className="brand-subtitle">Antarctic Navigation Decision Support</div>
          </div>
        </div>

        <div className="status-cluster">
          <span className="status-pill">Forecast: +{selectedForecast.replace('plus', '')} Days</span>
          <span className="status-pill">Risk Grid: Loaded</span>
          <span className="status-pill">Routes: {routes.length}</span>
        </div>
      </header>

      <main className="main-layout">
        <div className="map-column">
          <div className="map-toolbar">
            <div className="forecast-wrap">
              <label className="toolbar-label">Risk Forecast</label>
              <ForecastSelector
                selectedDay={selectedForecast}
                onSelectDay={setSelectedForecast}
                options={forecastOptions}
              />
            </div>
          </div>

          <AntarcticMap
            riskCells={riskCells}
            startPoint={startPoint}
            destinationPoint={destinationPoint}
            selectionMode={selectionMode}
            onMapClick={handleMapClick}
            routes={routes}
            selectedRoute={selectedRoute}
          />

          <div className="map-overlay-row">
            <MapLegend />
            <div className="route-legend-card">
              <div className="panel-header compact-header">
                <span className="eyebrow">Routes</span>
                <h3>Optimization Profiles</h3>
              </div>
              <div className="route-legend-list">
                <div className="route-legend-item safe"><span className="legend-swatch safe" /> Safest</div>
                <div className="route-legend-item balanced"><span className="legend-swatch balanced" /> Balanced</div>
                <div className="route-legend-item fuel"><span className="legend-swatch fuel" /> Fuel Efficient</div>
              </div>
            </div>
          </div>
        </div>

        <div className="side-column">
          <VoyagePanel
            startPoint={startPoint}
            destinationPoint={destinationPoint}
            selectionMode={selectionMode}
            setSelectionMode={setSelectionMode}
            onReset={handleReset}
            onCalculateRoutes={handleCalculateRoutes}
            canCalculate={canCalculate}
          />

          {routes.length > 0 && (
            <RouteComparison routes={routes} selectedRoute={selectedRoute} onSelectRoute={setSelectedRoute} />
          )}

          {selectedRoute && (
            <div className="route-details panel-card">
              <div className="panel-header compact-header">
                <span className="eyebrow">Selected Route</span>
                <h3>{selectedRoute.name}</h3>
              </div>

              <div className="detail-grid">
                <div><span>Distance</span><strong>{selectedRoute.distance_km.toLocaleString()} km</strong></div>
                <div><span>ETA</span><strong>{selectedRoute.eta_hours} h</strong></div>
                <div><span>Risk</span><strong>{selectedRoute.risk_score}</strong></div>
                <div><span>Fuel</span><strong>{selectedRoute.fuel_estimate.toLocaleString()} L</strong></div>
                <div><span>Cost</span><strong>{selectedRoute.cost_score}</strong></div>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}

export default App
