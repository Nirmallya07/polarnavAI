from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import xarray as xr
from pyproj import CRS, Transformer

from backend.config import config
from backend.services.copernicus_reader import CopernicusReader
from backend.services.era5_reader import ERA5WeatherReader
from backend.services.nsidc_reader import NSIDCSeaIceReader


class SeaIcePatchAssembler:
    """Assemble the 15x15 spatial patch history used by the packaged ConvLSTM."""

    CHANNELS = [
        "SIC",
        "wind_u10",
        "wind_v10",
        "wind_speed",
        "air_temperature",
        "pressure",
        "ocean_u",
        "ocean_v",
        "SST",
    ]
    PATCH_SIZE = 15
    HISTORY_LENGTH = 15

    def __init__(
        self,
        nsidc_reader: Any | None = None,
        era5_reader: Any | None = None,
        copernicus_reader: Any | None = None,
        patch_size: int = PATCH_SIZE,
        history_length: int = HISTORY_LENGTH,
    ) -> None:
        self.patch_size = max(1, int(patch_size))
        self.history_length = max(1, int(history_length))
        self.nsidc_reader = nsidc_reader or NSIDCSeaIceReader(data_dir=config.NSIDC_DIR)
        self.era5_reader = era5_reader or ERA5WeatherReader(data_dir=config.ERA5_DATA_DIR)
        self.copernicus_reader = copernicus_reader or CopernicusReader(data_dir=config.COPERNICUS_DIR)

    @staticmethod
    def _parse_utc(timestamp_utc: str | datetime) -> datetime:
        if isinstance(timestamp_utc, datetime):
            value = timestamp_utc
        else:
            value = str(timestamp_utc)
        if not isinstance(value, datetime):
            if value.endswith("Z"):
                value = value[:-1] + "+00:00"
            value = datetime.fromisoformat(value)
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _normalize_longitude(longitude: float) -> float:
        normalized = float(longitude)
        while normalized < -180.0:
            normalized += 360.0
        while normalized > 180.0:
            normalized -= 360.0
        return normalized

    def _load_nsidc_grid_snapshot(self) -> tuple[np.ndarray, np.ndarray]:
        candidate_files = sorted(Path(self.nsidc_reader.data_dir).glob("*.nc"))
        if not candidate_files:
            raise FileNotFoundError(f"No NSIDC NetCDF data found in {self.nsidc_reader.data_dir}")

        with xr.open_dataset(candidate_files[0], decode_times=True) as dataset:
            if "x" not in dataset.coords or "y" not in dataset.coords:
                raise ValueError("NSIDC dataset does not expose x/y grid coordinates")
            return np.asarray(dataset["x"].values, dtype=np.float64), np.asarray(dataset["y"].values, dtype=np.float64)

    def _patch_bounds_for_center(self, center_latitude: float, center_longitude: float) -> tuple[slice, slice, np.ndarray, np.ndarray]:
        x_coords, y_coords = self._load_nsidc_grid_snapshot()
        transformer = Transformer.from_crs(CRS.from_epsg(4326), CRS.from_epsg(3412), always_xy=True)
        x_target, y_target = transformer.transform(float(center_longitude), float(center_latitude))

        x_idx = int(np.abs(x_coords - x_target).argmin())
        y_idx = int(np.abs(y_coords - y_target).argmin())
        half = self.patch_size // 2
        x_start = max(0, x_idx - half)
        y_start = max(0, y_idx - half)
        x_end = min(len(x_coords), x_idx + half + 1)
        y_end = min(len(y_coords), y_idx + half + 1)

        if x_end - x_start < self.patch_size:
            pad_left = self.patch_size - (x_end - x_start)
            if x_start == 0:
                x_end = min(len(x_coords), x_end + pad_left)
            else:
                x_start = max(0, x_start - pad_left)
        if y_end - y_start < self.patch_size:
            pad_top = self.patch_size - (y_end - y_start)
            if y_start == 0:
                y_end = min(len(y_coords), y_end + pad_top)
            else:
                y_start = max(0, y_start - pad_top)

        x_slice = slice(x_start, x_end)
        y_slice = slice(y_start, y_end)
        x_patch = x_coords[x_slice]
        y_patch = y_coords[y_slice]
        if x_patch.size != self.patch_size or y_patch.size != self.patch_size:
            raise ValueError(
                f"Unable to assemble a full {self.patch_size}x{self.patch_size} NSIDC patch around ({center_latitude}, {center_longitude})."
            )
        return y_slice, x_slice, y_patch, x_patch

    def _patch_center_array(self, center_latitude: float, center_longitude: float) -> tuple[np.ndarray, np.ndarray]:
        _, _, y_coords, x_coords = self._patch_bounds_for_center(center_latitude, center_longitude)
        x_grid, y_grid = np.meshgrid(x_coords, y_coords, indexing="xy")
        back_transform = Transformer.from_crs(CRS.from_epsg(3412), CRS.from_epsg(4326), always_xy=True)
        lon_grid, lat_grid = back_transform.transform(x_grid, y_grid)
        return lat_grid.astype(np.float32), lon_grid.astype(np.float32)

    @staticmethod
    def _nearest_time_index(time_values: np.ndarray, target_time: datetime) -> int:
        target_value = np.datetime64(target_time.replace(tzinfo=None).isoformat())
        values = np.asarray(time_values, dtype="datetime64[ns]")
        return int(np.abs(values - target_value).argmin())

    def _read_sic_patch(self, timestamp_utc: str | datetime, center_latitude: float, center_longitude: float) -> np.ndarray:
        target_time = self._parse_utc(timestamp_utc)
        target_key = target_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        y_slice, x_slice, _, _ = self._patch_bounds_for_center(center_latitude, center_longitude)
        file_path = self.nsidc_reader.resolve_file_for_timestamp(target_key)

        with xr.open_dataset(file_path, decode_times=True) as dataset:
            time_name = next((name for name in ("time", "Date", "date") if name in dataset.coords), None)
            if time_name is None:
                raise ValueError(f"NSIDC dataset missing time coordinate: {file_path}")
            data_var = next((name for name in ("cdr_seaice_conc", "sea_ice_concentration", "sic", "ice_concentration") if name in dataset.data_vars), None)
            if data_var is None:
                data_var = next(iter(dataset.data_vars), None)
            if data_var is None:
                raise ValueError(f"No data variable found in NSIDC dataset {file_path}")

            nearest_idx = self._nearest_time_index(dataset[time_name].values, target_time)
            patch = dataset[data_var].isel({time_name: nearest_idx, "y": y_slice, "x": x_slice}).values
            patch = np.asarray(patch, dtype=np.float32)
            if patch.shape != (self.patch_size, self.patch_size):
                patch = np.pad(patch, ((0, self.patch_size - patch.shape[0]), (0, self.patch_size - patch.shape[1])), mode="edge")
            return patch[: self.patch_size, : self.patch_size]

    def _read_weather_patch(self, timestamp_utc: str | datetime, center_latitude: float, center_longitude: float) -> np.ndarray:
        target_time = self._parse_utc(timestamp_utc)
        time_key = target_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        lat_grid, lon_grid = self._patch_center_array(center_latitude, center_longitude)
        weather_month = target_time.strftime("%Y-%m")
        file_path = self.era5_reader._resolve_file_for_timestamp(time_key)
        if file_path is None:
            raise ValueError(f"No weather file for {time_key}")

        frame = pd.read_parquet(file_path)
        frame = frame.copy()
        frame["timestamp_utc"] = pd.to_datetime(frame["timestamp_utc"], utc=True)
        frame = frame[frame["timestamp_utc"] == pd.Timestamp(target_time)]
        if frame.empty:
            raise ValueError(f"No ERA5 weather rows for {time_key}")

        values = np.full((self.patch_size, self.patch_size, 5), np.nan, dtype=np.float32)
        for row in range(self.patch_size):
            for col in range(self.patch_size):
                target_lat = float(lat_grid[row, col])
                target_lon = self._normalize_longitude(float(lon_grid[row, col]))
                candidates = frame.copy()
                candidates["lat_delta"] = (candidates["latitude"] - target_lat).abs()
                candidates["lon_delta"] = (candidates["longitude"] - target_lon).abs()
                nearest = candidates.sort_values(["lat_delta", "lon_delta"]).iloc[0]
                values[row, col, 0] = float(nearest["wind_u10_mean"])
                values[row, col, 1] = float(nearest["wind_v10_mean"])
                values[row, col, 2] = float(nearest["wind_speed_mean"])
                values[row, col, 3] = float(nearest["air_temperature_c_mean"])
                values[row, col, 4] = float(nearest["mean_sea_level_pressure_hpa_mean"])
        return values

    def _read_ocean_patch(self, timestamp_utc: str | datetime, center_latitude: float, center_longitude: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        target_time = self._parse_utc(timestamp_utc)
        time_key = target_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        lat_grid, lon_grid = self._patch_center_array(center_latitude, center_longitude)
        file_path = self.copernicus_reader.resolve_file_for_timestamp(time_key)

        with xr.open_dataset(file_path, decode_times=True) as dataset:
            if "time" not in dataset.coords or "lat" not in dataset.coords or "lon" not in dataset.coords:
                raise ValueError(f"Copernicus dataset missing time/lat/lon coordinates: {file_path}")
            time_name = next((name for name in ("time", "Date", "date") if name in dataset.coords), None)
            if time_name is None:
                raise ValueError(f"Copernicus dataset missing time coordinate: {file_path}")
            selected = dataset.isel({time_name: self._nearest_time_index(dataset[time_name].values, target_time)})

            ocean_u = np.full((self.patch_size, self.patch_size), np.nan, dtype=np.float32)
            ocean_v = np.full((self.patch_size, self.patch_size), np.nan, dtype=np.float32)
            sst = np.full((self.patch_size, self.patch_size), np.nan, dtype=np.float32)
            lat_values = np.asarray(dataset["lat"].values, dtype=np.float32)
            lon_values = np.asarray(dataset["lon"].values, dtype=np.float32)

            for row in range(self.patch_size):
                for col in range(self.patch_size):
                    target_lat = float(lat_grid[row, col])
                    target_lon = self._normalize_longitude(float(lon_grid[row, col]))
                    lat_idx = int(np.abs(lat_values - target_lat).argmin())
                    lon_idx = int(np.abs(lon_values - target_lon).argmin())
                    ocean_u[row, col] = float(np.asarray(selected["uo"].isel(lat=lat_idx, lon=lon_idx).values, dtype=np.float32))
                    ocean_v[row, col] = float(np.asarray(selected["vo"].isel(lat=lat_idx, lon=lon_idx).values, dtype=np.float32))
                    sst[row, col] = float(np.asarray(selected["thetao"].isel(lat=lat_idx, lon=lon_idx).values, dtype=np.float32))
            return ocean_u, ocean_v, sst

    def build_model_input(
        self,
        center_latitude: float,
        center_longitude: float,
        history_timestamps: list[str | datetime],
    ) -> np.ndarray:
        timestamps = list(history_timestamps)
        if len(timestamps) < self.history_length:
            raise ValueError(
                f"Need at least {self.history_length} history timestamps to build the ConvLSTM tensor; received {len(timestamps)}."
            )
        timestamps = timestamps[-self.history_length :]

        encoder = np.empty((self.history_length, self.patch_size, self.patch_size, len(self.CHANNELS)), dtype=np.float32)
        for time_index, timestamp_utc in enumerate(timestamps):
            sic_patch = self._read_sic_patch(timestamp_utc, center_latitude, center_longitude)
            weather_patch = self._read_weather_patch(timestamp_utc, center_latitude, center_longitude)
            ocean_u_patch, ocean_v_patch, sst_patch = self._read_ocean_patch(timestamp_utc, center_latitude, center_longitude)

            encoder[time_index, :, :, 0] = sic_patch
            encoder[time_index, :, :, 1] = weather_patch[:, :, 0]
            encoder[time_index, :, :, 2] = weather_patch[:, :, 1]
            encoder[time_index, :, :, 3] = weather_patch[:, :, 2]
            encoder[time_index, :, :, 4] = weather_patch[:, :, 3]
            encoder[time_index, :, :, 5] = weather_patch[:, :, 4]
            encoder[time_index, :, :, 6] = ocean_u_patch
            encoder[time_index, :, :, 7] = ocean_v_patch
            encoder[time_index, :, :, 8] = sst_patch

        return encoder
