export function VoyagePanel({ startPoint, destinationPoint, selectionMode, setSelectionMode, onReset, onCalculateRoutes, canCalculate }) {
  return (
    <aside className="voyage-panel">
      <div className="panel-header">
        <span className="eyebrow">Voyage Planning</span>
        <h2>Route Setup</h2>
      </div>

      <div className="selection-controls">
        <button
          type="button"
          className={selectionMode === 'start' ? 'selector-button active' : 'selector-button'}
          onClick={() => setSelectionMode('start')}
        >
          Select Start
        </button>
        <button
          type="button"
          className={selectionMode === 'destination' ? 'selector-button active' : 'selector-button'}
          onClick={() => setSelectionMode('destination')}
        >
          Select Destination
        </button>
      </div>

      <div className="location-card">
        <label>Start</label>
        <div className="location-value">
          {startPoint ? `${startPoint.lat.toFixed(2)}°, ${startPoint.lng.toFixed(2)}°` : 'Not selected'}
        </div>
      </div>

      <div className="location-card">
        <label>Destination</label>
        <div className="location-value">
          {destinationPoint ? `${destinationPoint.lat.toFixed(2)}°, ${destinationPoint.lng.toFixed(2)}°` : 'Not selected'}
        </div>
      </div>

      <div className="panel-actions">
        <button type="button" className="primary-button" disabled={!canCalculate} onClick={onCalculateRoutes}>
          Calculate Routes
        </button>
        <button type="button" className="secondary-button" onClick={onReset}>
          Reset Points
        </button>
      </div>
    </aside>
  )
}
