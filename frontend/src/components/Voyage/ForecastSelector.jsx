export function ForecastSelector({ selectedDay, onSelectDay, options }) {
  return (
    <div className="forecast-selector" aria-label="Forecast day selector">
      {options.map((option) => (
        <button
          key={option.key}
          type="button"
          className={selectedDay === option.key ? 'forecast-pill active' : 'forecast-pill'}
          onClick={() => onSelectDay(option.key)}
        >
          {option.label}
        </button>
      ))}
    </div>
  )
}
