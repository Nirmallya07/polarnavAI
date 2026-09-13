import { formatRiskColor } from '../../data/mockRiskData'

export function MapLegend() {
  return (
    <div className="map-legend">
      <div className="panel-header compact-header">
        <span className="eyebrow">Legend</span>
        <h3>Risk Classes</h3>
      </div>

      <div className="legend-list">
        {[{ label: 'Low', score: '0-24', color: formatRiskColor(12) }, { label: 'Moderate', score: '25-49', color: formatRiskColor(37) }, { label: 'High', score: '50-69', color: formatRiskColor(60) }, { label: 'Extreme', score: '70-100', color: formatRiskColor(88) }].map((item) => (
          <div key={item.label} className="legend-row">
            <span className="legend-swatch" style={{ background: item.color }} aria-hidden="true" />
            <span className="legend-copy">
              <strong>{item.label}</strong>
              <small>{item.score}</small>
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
