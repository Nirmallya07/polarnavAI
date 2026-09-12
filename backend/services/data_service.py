"""Environmental data service for standardized latent inputs.

This is intentionally a development-friendly interface that can later be swapped
for real environmental data retrieval while preserving the same contract.
"""

from __future__ import annotations

from datetime import datetime, timezone


class DataService:
    """Standardize environmental inputs for lat/lon/timestamp queries."""

    @staticmethod
    def health_check() -> dict:
        return {"status": "ok", "service": "data-service"}

    @staticmethod
    def get_environment(latitude: float, longitude: float, timestamp_utc: str) -> dict:
        """Return a standardized environment state for a location and time.

        Values are intentionally development mocks until the real environmental
        sources are connected. They are deterministic and explicitly not a model
        output. They are meant to exercise the downstream risk and routing stack.
        """
        parsed = datetime.strptime(timestamp_utc, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
        seasonal_bias = abs(float(latitude)) / 90.0
        time_phase = ((parsed.hour * 60 + parsed.minute) / 1440.0) * 2.0

        return {
            "timestamp_utc": timestamp_utc,
            "latitude": float(latitude),
            "longitude": float(longitude),
            "sea_ice_concentration": round(min(1.0, max(0.0, seasonal_bias * 0.8 + 0.1)), 4),
            "wind_u10": round(10.0 * (0.4 + 0.6 * abs(float(longitude)) / 180.0) * (0.5 + time_phase / 2.0), 3),
            "wind_v10": round(-8.0 * (0.3 + seasonal_bias) * (0.5 + time_phase / 4.0), 3),
            "air_temperature": round(-8.0 - seasonal_bias * 18.0 + (time_phase * 6.0), 3),
            "ocean_u": round(0.4 * (1.0 + seasonal_bias) * (0.5 + time_phase), 3),
            "ocean_v": round(-0.3 * (0.7 + seasonal_bias) * (0.4 + time_phase), 3),
            "wave_height": round(1.0 + seasonal_bias * 2.3 + (time_phase * 0.5), 3),
            "wave_period": round(5.0 + seasonal_bias * 5.0 + time_phase * 2.0, 3),
        }
