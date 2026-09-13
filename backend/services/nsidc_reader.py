from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import xarray as xr
from pyproj import CRS, Transformer


class NSIDCSeaIceReader:
    """Read NOAA/NSIDC Level-3 daily sea-ice concentration fields.

    This provider targets the official NOAA/NSIDC CDR product G02202 V6.
    It reads a daily NetCDF file, selects the nearest valid time sample,
    and returns a normalized sea-ice concentration in the [0, 1] range.
    """

    def __init__(self, data_dir: str | None = None) -> None:
        self.data_dir = Path(data_dir or os.getenv("POLARNAV_NSIDC_DIR", "/mnt/polarnav-drive")).expanduser()
        self._file_cache: dict[tuple[int, int, int], Path] = {}

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

    def _find_daily_file(self, year: int, month: int, day: int) -> Path:
        key = (year, month, day)
        if key in self._file_cache:
            return self._file_cache[key]

        exact_pattern = f"*{year:04d}{month:02d}{day:02d}*.nc"
        exact_matches = sorted(self.data_dir.glob(exact_pattern))
        if exact_matches:
            selected = exact_matches[0]
            self._file_cache[key] = selected
            return selected

        candidates: list[tuple[int, Path]] = []
        for file_path in sorted(self.data_dir.glob("*.nc")):
            match = re.search(r"(\d{8})", file_path.name)
            if not match:
                continue
            file_date = datetime.strptime(match.group(1), "%Y%m%d")
            target_date = datetime(year, month, day)
            candidates.append((abs((file_date - target_date).days), file_path))

        if not candidates:
            raise FileNotFoundError(
                f"No NSIDC sea-ice NetCDF file found for {year:04d}-{month:02d}-{day:02d} in {self.data_dir}"
            )

        selected = min(candidates, key=lambda item: item[0])[1]
        self._file_cache[key] = selected
        return selected

    def resolve_file_for_timestamp(self, timestamp_utc: str) -> Path:
        parsed = self._parse_utc(timestamp_utc)
        return self._find_daily_file(parsed.year, parsed.month, parsed.day)

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

    @staticmethod
    def _normalize_sea_ice_fraction(value: float | None) -> float | None:
        if value is None:
            return None
        normalized = float(value)
        if np.isnan(normalized):
            return None
        # NOAA/NSIDC CDR often stores concentration as a percentage in [0, 100].
        # Convert to a [0, 1] float for the standardized environment schema.
        if normalized > 1.0:
            normalized /= 100.0
        if normalized < 0.0:
            return 0.0
        if normalized > 1.0:
            return 1.0
        return normalized

    def get_sea_ice_point(self, latitude: float, longitude: float, timestamp_utc: str) -> dict[str, float | None | str]:
        normalized_latitude = float(latitude)
        normalized_longitude = self._normalize_longitude(float(longitude))

        if not (-90.0 <= normalized_latitude <= 90.0):
            return {
                "timestamp_utc": timestamp_utc,
                "latitude": normalized_latitude,
                "longitude": normalized_longitude,
                "sea_ice_concentration": None,
                "source": "nsidc",
            }

        if not (-180.0 <= normalized_longitude <= 180.0):
            return {
                "timestamp_utc": timestamp_utc,
                "latitude": normalized_latitude,
                "longitude": normalized_longitude,
                "sea_ice_concentration": None,
                "source": "nsidc",
            }

        try:
            file_path = self.resolve_file_for_timestamp(timestamp_utc)
        except FileNotFoundError:
            return {
                "timestamp_utc": timestamp_utc,
                "latitude": normalized_latitude,
                "longitude": normalized_longitude,
                "sea_ice_concentration": None,
                "source": "nsidc",
                "error": "missing_file",
            }

        try:
            with xr.open_dataset(file_path, decode_times=True) as dataset:
                time_name = next((name for name in ("time", "Date", "date") if name in dataset.coords), None)
                lat_name = next((name for name in ("latitude", "lat", "y") if name in dataset.coords or name in dataset.dims), None)
                lon_name = next((name for name in ("longitude", "lon", "x") if name in dataset.coords or name in dataset.dims), None)

                if time_name is None or lat_name is None or lon_name is None:
                    return {
                        "timestamp_utc": timestamp_utc,
                        "latitude": normalized_latitude,
                        "longitude": normalized_longitude,
                        "sea_ice_concentration": None,
                        "source": "nsidc",
                        "error": "missing_dimensions",
                    }

                target_time = self._parse_utc(timestamp_utc)
                time_values = np.asarray(dataset[time_name].values, dtype="datetime64[ns]")
                target_value = np.datetime64(target_time.replace(tzinfo=None).isoformat())
                nearest_index = int(np.abs(time_values - target_value).argmin())
                time_point = dataset.isel({time_name: nearest_index})

                candidate_names = [
                    "cdr_seaice_conc",
                    "cdr_sea_ice_concentration",
                    "sea_ice_concentration",
                    "sic",
                    "ice_concentration",
                ]
                data_var = None
                for name in candidate_names:
                    if name in time_point.data_vars:
                        data_var = time_point[name]
                        break
                if data_var is None and len(time_point.data_vars) > 0:
                    data_var = next(iter(time_point.data_vars.values()))

                if data_var is None:
                    return {
                        "timestamp_utc": timestamp_utc,
                        "latitude": normalized_latitude,
                        "longitude": normalized_longitude,
                        "sea_ice_concentration": None,
                        "source": "nsidc",
                        "error": "missing_data_var",
                    }

                data_array = data_var
                lat_values = None
                lon_values = None
                lat_dim = None
                lon_dim = None

                geographic_lat_names = tuple(name for name in ("latitude", "lat") if name in time_point.coords)
                geographic_lon_names = tuple(name for name in ("longitude", "lon") if name in time_point.coords)
                projected_x_names = tuple(name for name in ("x",) if name in time_point.coords)
                projected_y_names = tuple(name for name in ("y",) if name in time_point.coords)

                if geographic_lat_names:
                    lat_name = geographic_lat_names[0]
                    lat_values = np.asarray(time_point.coords[lat_name].values)
                    lat_dim = lat_name
                if geographic_lon_names:
                    lon_name = geographic_lon_names[0]
                    lon_values = np.asarray(time_point.coords[lon_name].values)
                    lon_dim = lon_name

                if lat_values is not None and lon_values is not None and not projected_x_names and not projected_y_names:
                    if lat_values.ndim == 1 and lon_values.ndim == 1:
                        y_index = int(np.abs(lat_values - normalized_latitude).argmin())
                        x_index = int(np.abs(lon_values - normalized_longitude).argmin())
                        value = self._as_float(data_array.isel({lat_dim: y_index, lon_dim: x_index}).item())
                    else:
                        lat_matrix = np.asarray(lat_values)
                        lon_matrix = np.asarray(lon_values)
                        lon_delta = (lon_matrix - normalized_longitude + 180.0) % 360.0 - 180.0
                        distance = (lat_matrix - normalized_latitude) ** 2 + lon_delta ** 2
                        y_index, x_index = np.unravel_index(np.argmin(distance), distance.shape)

                        y_dim_name = next((dim for dim in data_array.dims if dim in {"y", "lat", "latitude"}), data_array.dims[0])
                        x_dim_name = next((dim for dim in data_array.dims if dim in {"x", "lon", "longitude"}), data_array.dims[-1])
                        value = self._as_float(data_array.isel({y_dim_name: y_index, x_dim_name: x_index}).item())
                elif projected_x_names and projected_y_names:
                    x_values = np.asarray(time_point[projected_x_names[0]].values, dtype=np.float64)
                    y_values = np.asarray(time_point[projected_y_names[0]].values, dtype=np.float64)
                    x_range = np.nanmax(np.abs(x_values)) if x_values.size else 0.0
                    y_range = np.nanmax(np.abs(y_values)) if y_values.size else 0.0

                    if x_range <= 180.0 and y_range <= 90.0:
                        y_index = int(np.abs(y_values - normalized_latitude).argmin())
                        x_index = int(np.abs(x_values - normalized_longitude).argmin())
                        value = self._as_float(data_array.isel({projected_y_names[0]: y_index, projected_x_names[0]: x_index}).item())
                    else:
                        transformer = Transformer.from_crs(CRS.from_epsg(4326), CRS.from_epsg(3412), always_xy=True)
                        target_x, target_y = transformer.transform(normalized_longitude, normalized_latitude)
                        x_index = int(np.abs(x_values - target_x).argmin())
                        y_index = int(np.abs(y_values - target_y).argmin())
                        value = self._as_float(data_array.isel({projected_y_names[0]: y_index, projected_x_names[0]: x_index}).item())
                else:
                    return {
                        "timestamp_utc": timestamp_utc,
                        "latitude": normalized_latitude,
                        "longitude": normalized_longitude,
                        "sea_ice_concentration": None,
                        "source": "nsidc",
                        "error": "missing_lat_lon_coords",
                    }

                normalized_value = self._normalize_sea_ice_fraction(value)
                return {
                    "timestamp_utc": timestamp_utc,
                    "latitude": normalized_latitude,
                    "longitude": normalized_longitude,
                    "sea_ice_concentration": normalized_value,
                    "source": "nsidc",
                }
        except (OSError, ValueError, KeyError) as exc:
            return {
                "timestamp_utc": timestamp_utc,
                "latitude": normalized_latitude,
                "longitude": normalized_longitude,
                "sea_ice_concentration": None,
                "source": "nsidc",
                "error": str(exc),
            }
