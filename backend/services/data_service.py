"""Environmental data service for standardized latent inputs.

This public interface remains stable while the implementation is migrated from
mock values to real Copernicus ocean observations. Other environmental sources
(NSIDC, ERA5, ML predictions) remain separate layers and are intentionally not
fabricated here.
"""

from __future__ import annotations

from backend.config import config
from backend.services.copernicus_reader import CopernicusReader


class DataService:
    """Standardize environmental inputs for lat/lon/timestamp queries."""

    _copernicus_reader = CopernicusReader(data_dir=config.COPERNICUS_DIR)

    @staticmethod
    def health_check() -> dict:
        return {"status": "ok", "service": "data-service"}

    @staticmethod
    def get_environment(latitude: float, longitude: float, timestamp_utc: str) -> dict:
        """Return a standardized environment state for a location and time.

        The canonical interface remains unchanged. Currently, the real ocean layer is
        backed by the mounted Copernicus dataset, while the other required fields are
        intentionally left as null until the corresponding source is integrated.
        """
        try:
            ocean_state = DataService._copernicus_reader.get_ocean_point(latitude, longitude, timestamp_utc)
        except Exception:
            ocean_state = {
                "timestamp_utc": timestamp_utc,
                "latitude": float(latitude),
                "longitude": float(longitude),
                "ocean_u": None,
                "ocean_v": None,
                "source": "copernicus",
                "error": "reader_exception",
            }

        return {
            "timestamp_utc": timestamp_utc,
            "latitude": float(latitude),
            "longitude": float(longitude),
            "sea_ice_concentration": None,
            "wind_u10": None,
            "wind_v10": None,
            "air_temperature": None,
            "ocean_u": ocean_state.get("ocean_u"),
            "ocean_v": ocean_state.get("ocean_v"),
            "wave_height": None,
            "wave_period": None,
        }
