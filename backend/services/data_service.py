"""Environmental data service for standardized latent inputs.

This public interface remains stable while the implementation is migrated from
mock values to real Copernicus ocean observations. Other environmental sources
(NSIDC, ERA5, ML predictions) remain separate layers and are intentionally not
fabricated here.
"""

from __future__ import annotations

from backend.config import config
from backend.services.copernicus_reader import CopernicusReader
from backend.services.era5_reader import ERA5WeatherReader
from backend.services.nsidc_reader import NSIDCSeaIceReader


class DataService:
    """Standardize environmental inputs for lat/lon/timestamp queries."""

    _copernicus_reader = CopernicusReader(data_dir=config.COPERNICUS_DIR)
    _nsidc_reader = NSIDCSeaIceReader(data_dir=config.NSIDC_DIR)
    _era5_reader = ERA5WeatherReader(data_dir=config.ERA5_DATA_DIR)

    @staticmethod
    def health_check() -> dict:
        return {"status": "ok", "service": "data-service"}

    @staticmethod
    def get_environment(latitude: float, longitude: float, timestamp_utc: str) -> dict:
        """Return a standardized environment state for a location and time.

        The canonical interface remains unchanged. The current live layers are:
        - Copernicus ocean currents
        - NOAA/NSIDC sea-ice concentration

        ERA5 and the full 9-channel model input builder remain intentionally out of
        scope for this incremental step.
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

        try:
            sea_ice_state = DataService._nsidc_reader.get_sea_ice_point(latitude, longitude, timestamp_utc)
        except Exception:
            sea_ice_state = {
                "timestamp_utc": timestamp_utc,
                "latitude": float(latitude),
                "longitude": float(longitude),
                "sea_ice_concentration": None,
                "source": "nsidc",
                "error": "reader_exception",
            }

        try:
            weather_state = DataService._era5_reader.get_weather_point(latitude, longitude, timestamp_utc)
        except Exception:
            weather_state = {
                "timestamp_utc": timestamp_utc,
                "latitude": float(latitude),
                "longitude": float(longitude),
                "wind_u10": None,
                "wind_v10": None,
                "wind_speed": None,
                "air_temperature": None,
                "pressure": None,
                "source": "era5",
                "error": "reader_exception",
            }

        return {
            "timestamp_utc": timestamp_utc,
            "latitude": float(latitude),
            "longitude": float(longitude),
            "sea_ice_concentration": sea_ice_state.get("sea_ice_concentration"),
            "wind_u10": weather_state.get("wind_u10"),
            "wind_v10": weather_state.get("wind_v10"),
            "air_temperature": weather_state.get("air_temperature"),
            "ocean_u": ocean_state.get("ocean_u"),
            "ocean_v": ocean_state.get("ocean_v"),
            "wave_height": None,
            "wave_period": None,
            "source": sea_ice_state.get("source", "nsidc"),
            "weather_source": weather_state.get("source", "era5"),
            "pressure": weather_state.get("pressure"),
            "wind_speed": weather_state.get("wind_speed"),
        }
