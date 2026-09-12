from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import xarray as xr


class CopernicusReader:
    """Read monthly Copernicus Marine ocean fields by nearest lat/lon/time."""

    def __init__(self, data_dir: str | None = None) -> None:
        self.data_dir = Path(data_dir or os.getenv("POLARNAV_COPERNICUS_DIR", "/mnt/polarnav-drive")).expanduser()
        self._file_cache: dict[tuple[int, int], Path] = {}

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

    def _find_monthly_file(self, year: int, month: int) -> Path:
        key = (year, month)
        if key in self._file_cache:
            return self._file_cache[key]

        pattern = f"*_{year:04d}-{month:02d}-*T00-00-00-*.nc"
        matches = sorted(self.data_dir.glob(pattern))
        if not matches:
            raise FileNotFoundError(
                f"No Copernicus monthly NetCDF file found for {year:04d}-{month:02d} "
                f"in {self.data_dir}"
            )

        selected = matches[0]
        self._file_cache[key] = selected
        return selected

    def resolve_file_for_timestamp(self, timestamp_utc: str) -> Path:
        parsed = self._parse_utc(timestamp_utc)
        return self._find_monthly_file(parsed.year, parsed.month)

    @staticmethod
    def _as_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return None
        if np.isnan(numeric):
            return None
        return numeric

    def get_ocean_point(self, latitude: float, longitude: float, timestamp_utc: str) -> dict[str, float | None | str]:
        normalized_latitude = float(latitude)
        normalized_longitude = self._normalize_longitude(float(longitude))

        if not (-75.0 <= normalized_latitude <= -45.0):
            return {
                "timestamp_utc": timestamp_utc,
                "latitude": normalized_latitude,
                "longitude": normalized_longitude,
                "ocean_u": None,
                "ocean_v": None,
                "source": "copernicus",
            }

        if not (-180.0 <= normalized_longitude <= 180.0):
            return {
                "timestamp_utc": timestamp_utc,
                "latitude": normalized_latitude,
                "longitude": normalized_longitude,
                "ocean_u": None,
                "ocean_v": None,
                "source": "copernicus",
            }

        try:
            file_path = self.resolve_file_for_timestamp(timestamp_utc)
        except FileNotFoundError:
            return {
                "timestamp_utc": timestamp_utc,
                "latitude": normalized_latitude,
                "longitude": normalized_longitude,
                "ocean_u": None,
                "ocean_v": None,
                "source": "copernicus",
                "error": "missing_file",
            }

        try:
            with xr.open_dataset(file_path, decode_times=True) as dataset:
                if "time" not in dataset.coords or "lat" not in dataset.coords or "lon" not in dataset.coords:
                    return {
                        "timestamp_utc": timestamp_utc,
                        "latitude": normalized_latitude,
                        "longitude": normalized_longitude,
                        "ocean_u": None,
                        "ocean_v": None,
                        "source": "copernicus",
                        "error": "missing_dimensions",
                    }

                time_index = dataset.indexes["time"]
                target_time = self._parse_utc(timestamp_utc)
                time_values = np.asarray(time_index.values, dtype="datetime64[ns]")
                target_value = np.datetime64(target_time.replace(tzinfo=None).isoformat())
                nearest_index = int(np.abs(time_values - target_value).argmin())
                nearest_time_value = time_index[nearest_index]

                selected = dataset.sel(time=nearest_time_value, method="nearest")
                selected_point = selected.sel(lat=normalized_latitude, lon=normalized_longitude, method="nearest")

                valid_mask = selected_point.get("valid_ocean_mask")
                if valid_mask is not None:
                    mask_value = self._as_float(valid_mask.item())
                    if mask_value is not None and mask_value == 0.0:
                        return {
                            "timestamp_utc": timestamp_utc,
                            "latitude": normalized_latitude,
                            "longitude": normalized_longitude,
                            "ocean_u": None,
                            "ocean_v": None,
                            "source": "copernicus",
                        }

                raw_uo = self._as_float(selected_point["uo"].item())
                raw_vo = self._as_float(selected_point["vo"].item())
                return {
                    "timestamp_utc": timestamp_utc,
                    "latitude": normalized_latitude,
                    "longitude": normalized_longitude,
                    "ocean_u": raw_uo,
                    "ocean_v": raw_vo,
                    "source": "copernicus",
                }
        except (OSError, ValueError, KeyError) as exc:
            return {
                "timestamp_utc": timestamp_utc,
                "latitude": normalized_latitude,
                "longitude": normalized_longitude,
                "ocean_u": None,
                "ocean_v": None,
                "source": "copernicus",
                "error": str(exc),
            }
