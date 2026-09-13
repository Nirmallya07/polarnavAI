export function RouteComparison({ routes, selectedRoute, onSelectRoute }) {
  return (
    <div className="route-comparison">
      <div className="panel-header compact-header">
        <span className="eyebrow">Optimized Routes</span>
        <h3>Compare Profiles</h3>
      </div>

      <div className="route-table">
        {routes.map((route) => (
          <button
            key={route.mode}
            type="button"
            className={selectedRoute?.mode === route.mode ? 'route-row selected' : 'route-row'}
            onClick={() => onSelectRoute(route)}
          >
            <div className="route-name-wrap">
              <span className="route-color" style={{ background: route.color }} aria-hidden="true" />
              <span>{route.name}</span>
            </div>
            <span>{route.distance_km.toLocaleString()} km</span>
            <span>{route.eta_hours} h</span>
            <span>{route.risk_score}</span>
            <span>{route.fuel_estimate.toLocaleString()} L</span>
          </button>
        ))}
      </div>
    </div>
  )
}
