import { Circle, CircleMarker, MapContainer, Marker, Popup, TileLayer, useMapEvents } from 'react-leaflet'
import L from 'leaflet'
import { formatRiskColor } from '../../data/mockRiskData'

const startIcon = new L.DivIcon({
  className: 'custom-marker start-marker',
  html: '<span class="marker-dot start-dot"></span>',
  iconSize: [18, 18],
  iconAnchor: [9, 9],
})

const destinationIcon = new L.DivIcon({
  className: 'custom-marker destination-marker',
  html: '<span class="marker-dot destination-dot"></span>',
  iconSize: [18, 18],
  iconAnchor: [9, 9],
})

function MapInteraction({ onMapClick }) {
  useMapEvents({
    click: (event) => {
      onMapClick(event.latlng)
    },
  })

  return null
}

export function AntarcticMap({ riskCells, startPoint, destinationPoint, selectionMode, onMapClick }) {
  return (
    <div className="map-frame">
      <MapContainer center={[-68, 18]} zoom={3} minZoom={2} maxZoom={8} scrollWheelZoom className="antarctic-map">
        <TileLayer
          attribution='&copy; OpenStreetMap contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        <MapInteraction onMapClick={onMapClick} />

        {riskCells.map((cell, index) => (
          <CircleMarker
            key={`${cell.latitude}-${cell.longitude}-${index}`}
            center={[cell.latitude, cell.longitude]}
            radius={7}
            pathOptions={{
              color: formatRiskColor(cell.risk_score),
              fillColor: formatRiskColor(cell.risk_score),
              fillOpacity: 0.7,
              weight: 1,
            }}
          >
            <Popup>
              <div className="risk-popup">
                <strong>Risk Score</strong>
                <div>{cell.risk_score} / 100</div>
                <div>{cell.risk_level}</div>
                <small>
                  {cell.latitude.toFixed(2)}°S, {cell.longitude.toFixed(2)}°E
                </small>
              </div>
            </Popup>
          </CircleMarker>
        ))}

        {startPoint && (
          <Marker position={[startPoint.lat, startPoint.lng]} icon={startIcon}>
            <Popup>Start: {startPoint.lat.toFixed(2)}°, {startPoint.lng.toFixed(2)}°</Popup>
          </Marker>
        )}

        {destinationPoint && (
          <Marker position={[destinationPoint.lat, destinationPoint.lng]} icon={destinationIcon}>
            <Popup>Destination: {destinationPoint.lat.toFixed(2)}°, {destinationPoint.lng.toFixed(2)}°</Popup>
          </Marker>
        )}

        {selectionMode && (
          <Circle center={[-68, 18]} radius={150000} pathOptions={{ color: '#4fd1c5', fillColor: '#4fd1c5', fillOpacity: 0.08, weight: 1 }} />
        )}
      </MapContainer>
    </div>
  )
}
