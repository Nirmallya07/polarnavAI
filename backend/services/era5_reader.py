from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


class ERA5WeatherReader:
    """Read locally available Copernicus ERA5 weather data for a point query.

    This provider is intentionally scoped to historical/latest-available ERA5
    weather fields needed by the sea-ice model. It does not build the full 9-channel
    input tensor or connect to external forecast systems.
    """

    REQUIRED_FIELDS = {
        "wind_u10": "wind_u10_mean",
        "wind_v10": "wind_v10_mean",
        "wind_speed": "wind_speed_mean",
        "air_temperature": "air_temperature_c_mean",
        "pressure": "mean_sea_level_pressure_hpa_mean",
    }

    def __init__(self, data_dir: str | None = None) -> None:
        self.data_dir = Path(data_dir or os.getenv("ERA5_DATA_DIR", "/mnt/polarnav-models/PolarNav_Weather_Dataset_2023/daily")).expanduser()

    @staticmethod
    def _normalize_longitude(longitude: float) -> float:
        normalized = float(longitude)
        while normalized < -180.0:
            normalized += 360.0
        while normalized > 180.0:
            normalized -= 360.0
        return normalized

    @staticmethod
    def _parse_utc(timestamp_utc: str) -> datetime:
        if not isinstance(timestamp_utc, str):
            raise ValueError("timestamp_utc must be a UTC ISO 8601 string")
        if not timestamp_utc.endswith("Z"):
            raise ValueError("timestamp_utc must be in UTC format ending with Z")
        try:
            return datetime.strptime(timestamp_utc, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        except ValueError as exc:
            raise ValueError(f"Malformed UTC timestamp: {timestamp_utc}") from exc

    @staticmethod
    def _as_float(value: Any) -> float | None:
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return None
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return None
        if np.isnan(numeric):
            return None
        return numeric

    @staticmethod
    def _to_celsius(kelvin_value: float | None) -> float | None:
        if kelvin_value is None:
            return None
        numeric = float(kelvin_value)
        if numeric > 200.0:
            return round(numeric - 273.15, 6)
        return round(numeric, 6)

    @staticmethod
    def _to_hpa(pa_value: float | None) -> float | None:
        if pa_value is None:
            return None
        numeric = float(pa_value)
        if numeric > 2000.0:
            return round(numeric / 100.0, 6)
        return round(numeric, 6)

    @staticmethod
    def _wind_speed_from_components(u_component: float | None, v_component: float | None) -> float | None:
        if u_component is None or v_component is None:
            return None
        return float(np.hypot(float(u_component), float(v_component)))

    @staticmethod
    def _timestamp_to_date_key(timestamp_utc: str) -> str:
        parsed = ERA5WeatherReader._parse_utc(timestamp_utc)
        return parsed.strftime("%Y-%m-%d")

    def _resolve_file_for_timestamp(self, timestamp_utc: str) -> Path | None:
        target_date = self._timestamp_to_date_key(timestamp_utc)
        candidates = sorted(self.data_dir.glob("*.parquet"))
        if not candidates:
            return None

        if any(candidate.name.startswith("weather_antarctic_") for candidate in candidates):
            target_name = f"weather_antarctic_{target_date[0:4]}_{target_date[5:7]}_daily.parquet"
            for candidate in candidates:
                if candidate.name == target_name:
                    return candidate

        matches = []
        for candidate in candidates:
            match = re.search(r"(\d{4})_(\d{2})", candidate.name)
            if not match:
                continue
            year, month = match.groups()
            month_key = f"{year}-{month}"
            if month_key == target_date[:7]:
                matches.append(candidate)
        if matches:
            return matches[0]

        return None

    def get_weather_point(self, latitude: float, longitude: float, timestamp_utc: str) -> dict[str, Any]:
        normalized_latitude = float(latitude)
        normalized_longitude = self._normalize_longitude(float(longitude))

        if not (-90.0 <= normalized_latitude <= 90.0):
            return {
                "timestamp_utc": timestamp_utc,
                "latitude": normalized_latitude,
                "longitude": normalized_longitude,
                "wind_u10": None,
                "wind_v10": None,
                "wind_speed": None,
                "air_temperature": None,
                "pressure": None,
                "error": "latitude_out_of_range",
            }

        if not (-180.0 <= normalized_longitude <= 180.0):
            return {
                "timestamp_utc": timestamp_utc,
                "latitude": normalized_latitude,
                "longitude": normalized_longitude,
                "wind_u10": None,
                "wind_v10": None,
                "wind_speed": None,
                "air_temperature": None,
                "pressure": None,
                "error": "longitude_out_of_range",
            }

        try:
            parsed_timestamp = self._parse_utc(timestamp_utc)
        except ValueError as exc:
            return {
                "timestamp_utc": timestamp_utc,
                "latitude": normalized_latitude,
                "longitude": normalized_longitude,
                "wind_u10": None,
                "wind_v10": None,
                "wind_speed": None,
                "air_temperature": None,
                "pressure": None,
                "error": str(exc),
            }

        file_path = self._resolve_file_for_timestamp(timestamp_utc)
        if file_path is None:
            return {
                "timestamp_utc": timestamp_utc,
                "latitude": normalized_latitude,
                "longitude": normalized_longitude,
                "wind_u10": None,
                "wind_v10": None,
                "wind_speed": None,
                "air_temperature": None,
                "pressure": None,
                "error": "timestamp_not_available",
            }

        try:
            frame = pd.read_parquet(file_path)
        except Exception as exc:
            return {
                "timestamp_utc": timestamp_utc,
                "latitude": normalized_latitude,
                "longitude": normalized_longitude,
                "wind_u10": None,
                "wind_v10": None,
                "wind_speed": None,
                "air_temperature": None,
                "pressure": None,
                "error": f"dataset_read_error: {exc}",
            }

        if "timestamp_utc" not in frame.columns:
            return {
                "timestamp_utc": timestamp_utc,
                "latitude": normalized_latitude,
                "longitude": normalized_longitude,
                "wind_u10": None,
                "wind_v10": None,
                "wind_speed": None,
                "air_temperature": None,
                "pressure": None,
                "error": "missing_timestamp_column",
            }

        frame = frame.copy()
        frame["timestamp_utc"] = pd.to_datetime(frame["timestamp_utc"], utc=True)
        target_time = pd.Timestamp(parsed_timestamp)
        matching = frame[frame["timestamp_utc"] == target_time]
        if matching.empty:
            return {
                "timestamp_utc": timestamp_utc,
                "latitude": normalized_latitude,
                "longitude": normalized_longitude,
                "wind_u10": None,
                "wind_v10": None,
                "wind_speed": None,
                "air_temperature": None,
                "pressure": None,
                "error": "timestamp_not_available",
            }

        if {"latitude", "longitude"}.difference(frame.columns):
            return {
                "timestamp_utc": timestamp_utc,
                "latitude": normalized_latitude,
                "longitude": normalized_longitude,
                "wind_u10": None,
                "wind_v10": None,
                "wind_speed": None,
                "air_temperature": None,
                "pressure": None,
                "error": "missing_lat_lon_columns",
            }

        candidates = matching.copy()
        if not candidates.empty:
            candidates["lat_delta"] = (candidates["latitude"] - normalized_latitude).abs()
            candidates["lon_delta"] = (candidates["longitude"] - normalized_longitude).abs()
            nearest = candidates.sort_values(["lat_delta", "lon_delta"]).iloc[0]
        else:
            nearest = None

        if nearest is None:
            return {
                "timestamp_utc": timestamp_utc,
                "latitude": normalized_latitude,
                "longitude": normalized_longitude,
                "wind_u10": None,
                "wind_v10": None,
                "wind_speed": None,
                "air_temperature": None,
                "pressure": None,
                "error": "timestamp_not_available",
            }

        raw_u = self._as_float(nearest.get("wind_u10_mean"))
        raw_v = self._as_float(nearest.get("wind_v10_mean"))
        raw_air = self._as_float(nearest.get("air_temperature_c_mean"))
        raw_pressure = self._as_float(nearest.get("mean_sea_level_pressure_hpa_mean"))
        raw_wind_speed = self._as_float(nearest.get("wind_speed_mean"))

        wind_u10 = raw_u
        wind_v10 = raw_v
        air_temperature = self._to_celsius(raw_air)
        pressure = self._to_hpa(raw_pressure)
        wind_speed = raw_wind_speed if raw_wind_speed is not None else self._wind_speed_from_components(raw_u, raw_v)

        if raw_u is not None and raw_v is not None and raw_wind_speed is None:
            wind_speed = self._wind_speed_from_components(raw_u, raw_v)

        return {
            "timestamp_utc": timestamp_utc,
            "latitude": float(normalized_latitude),
            "longitude": float(normalized_longitude),
            "wind_u10": wind_u10,
            "wind_v10": wind_v10,
            "wind_speed": wind_speed,
            "air_temperature": air_temperature,
            "pressure": pressure,
            "source": "Copernicus ERA5 hourly single levels",
            "dataset": "reanalysis-era5-single-levels",
            "raw_values": {
                "wind_u10_mean": raw_u,
                "wind_v10_mean": raw_v,
                "wind_speed_mean": raw_wind_speed,
                "air_temperature_c_mean": raw_air,
                "mean_sea_level_pressure_hpa_mean": raw_pressure,
            },
        }
