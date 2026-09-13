from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from backend.config import config
from backend.services.copernicus_reader import CopernicusReader
from backend.services.era5_reader import ERA5WeatherReader
from backend.services.nsidc_reader import NSIDCSeaIceReader


class EnvironmentalHistoryCoordinator:
    """Coordinate the synchronized temporal history across NSIDC, ERA5, and Copernicus providers.

    This service intentionally does not build the ConvLSTM tensor, invoke the ML model,
    or perform route generation. It only determines the synchronized environmental window.
    """

    def __init__(
        self,
        nsidc_reader: Any | None = None,
        era5_reader: Any | None = None,
        copernicus_reader: Any | None = None,
        history_length: int = 15,
    ) -> None:
        self.history_length = max(1, int(history_length))
        self.nsidc_reader = nsidc_reader or NSIDCSeaIceReader(data_dir=config.NSIDC_DIR)
        self.era5_reader = era5_reader or ERA5WeatherReader(data_dir=config.ERA5_DATA_DIR)
        self.copernicus_reader = copernicus_reader or CopernicusReader(data_dir=config.COPERNICUS_DIR)

    @staticmethod
    def _parse_utc(timestamp_utc: str | datetime) -> datetime:
        if isinstance(timestamp_utc, datetime):
            parsed = timestamp_utc
        elif isinstance(timestamp_utc, str):
            value = timestamp_utc.strip()
            if value.endswith("Z"):
                value = value[:-1] + "+00:00"
            parsed = datetime.fromisoformat(value)
        else:
            raise ValueError("timestamp_utc must be a UTC ISO 8601 string or datetime")

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    @classmethod
    def _normalize_utc(cls, timestamp_utc: str | datetime) -> str:
        return cls._parse_utc(timestamp_utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    @staticmethod
    def _coerce_timestamp(value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return EnvironmentalHistoryCoordinator._normalize_utc(value)
        if isinstance(value, str):
            return EnvironmentalHistoryCoordinator._normalize_utc(value)
        return str(value)

    @staticmethod
    def _timestamp_sequence(start_utc: str | datetime, end_utc: str | datetime) -> list[str]:
        start_dt = EnvironmentalHistoryCoordinator._parse_utc(start_utc)
        end_dt = EnvironmentalHistoryCoordinator._parse_utc(end_utc)
        timestamps: list[str] = []
        cursor = start_dt
        while cursor <= end_dt:
            timestamps.append(cursor.strftime("%Y-%m-%dT%H:%M:%SZ"))
            cursor += timedelta(days=1)
        return timestamps

    @staticmethod
    def _normalize_timestamp_set(values: list[str | datetime]) -> set[str]:
        normalized: set[str] = set()
        for value in values:
            normalized.add(EnvironmentalHistoryCoordinator._normalize_utc(value))
        return normalized

    @staticmethod
    def _source_latest_timestamp(source: Any) -> str | None:
        if source is None:
            return None

        if hasattr(source, "latest_available_timestamp"):
            latest = source.latest_available_timestamp()
            return EnvironmentalHistoryCoordinator._coerce_timestamp(latest)

        if hasattr(source, "list_available_timestamps"):
            values = list(source.list_available_timestamps())
            if not values:
                return None
            parsed = [EnvironmentalHistoryCoordinator._parse_utc(value) for value in values]
            return EnvironmentalHistoryCoordinator._normalize_utc(max(parsed))

        data_dir = getattr(source, "data_dir", None)
        if data_dir is None:
            return None

        path = Path(data_dir)
        if not path.exists():
            return None

        if isinstance(source, NSIDCSeaIceReader):
            records: list[datetime] = []
            for file_path in sorted(path.glob("*.nc")):
                try:
                    import xarray as xr

                    with xr.open_dataset(file_path, decode_times=True) as dataset:
                        if "time" in dataset.coords:
                            values = dataset["time"].values
                            if len(values):
                                records.extend(datetime.fromisoformat(str(v).replace("Z", "+00:00")) for v in values)
                except Exception:
                    continue
            if not records:
                return None
            return EnvironmentalHistoryCoordinator._normalize_utc(max(records))

        if isinstance(source, ERA5WeatherReader):
            timestamps: list[datetime] = []
            for file_path in sorted(path.glob("*.parquet")):
                try:
                    import pandas as pd

                    frame = pd.read_parquet(file_path)
                    if "timestamp_utc" in frame.columns:
                        values = pd.to_datetime(frame["timestamp_utc"], utc=True)
                        timestamps.extend(v.to_pydatetime() for v in values)
                except Exception:
                    continue
            if not timestamps:
                return None
            return EnvironmentalHistoryCoordinator._normalize_utc(max(timestamps))

        if isinstance(source, CopernicusReader):
            records: list[datetime] = []
            for file_path in sorted(path.glob("*.nc")):
                try:
                    import xarray as xr

                    with xr.open_dataset(file_path, decode_times=True) as dataset:
                        if "time" in dataset.coords:
                            values = dataset["time"].values
                            if len(values):
                                records.extend(datetime.fromisoformat(str(v).replace("Z", "+00:00")) for v in values)
                except Exception:
                    continue
            if not records:
                return None
            return EnvironmentalHistoryCoordinator._normalize_utc(max(records))

        return None

    @staticmethod
    def _all_source_timestamps(source: Any) -> list[str]:
        if source is None:
            return []

        if hasattr(source, "list_available_timestamps"):
            return [EnvironmentalHistoryCoordinator._normalize_utc(value) for value in source.list_available_timestamps()]

        data_dir = getattr(source, "data_dir", None)
        if data_dir is None:
            return []

        path = Path(data_dir)
        if not path.exists():
            return []

        timestamps: set[datetime] = set()
        if isinstance(source, NSIDCSeaIceReader):
            for file_path in sorted(path.glob("*.nc")):
                try:
                    import xarray as xr

                    with xr.open_dataset(file_path, decode_times=True) as dataset:
                        if "time" in dataset.coords:
                            for value in dataset["time"].values:
                                timestamps.add(EnvironmentalHistoryCoordinator._parse_utc(str(value).replace(" ", "T")))
                except Exception:
                    continue
        elif isinstance(source, ERA5WeatherReader):
            for file_path in sorted(path.glob("*.parquet")):
                try:
                    import pandas as pd

                    frame = pd.read_parquet(file_path)
                    if "timestamp_utc" in frame.columns:
                        timestamps.update(pd.to_datetime(frame["timestamp_utc"], utc=True).dt.to_pydatetime())
                except Exception:
                    continue
        elif isinstance(source, CopernicusReader):
            for file_path in sorted(path.glob("*.nc")):
                try:
                    import xarray as xr

                    with xr.open_dataset(file_path, decode_times=True) as dataset:
                        if "time" in dataset.coords:
                            for value in dataset["time"].values:
                                timestamps.add(EnvironmentalHistoryCoordinator._parse_utc(str(value).replace(" ", "T")))
                except Exception:
                    continue

        return [EnvironmentalHistoryCoordinator._normalize_utc(value) for value in sorted(timestamps)]

    @staticmethod
    def _record_for_source(source: Any, source_name: str, latitude: float, longitude: float, timestamp_utc: str) -> dict[str, Any]:
        if source is None:
            return {"timestamp_utc": timestamp_utc, "status": "missing_source"}

        method_name = {
            "nsidc": "get_sea_ice_point",
            "era5": "get_weather_point",
            "copernicus": "get_ocean_point",
        }.get(source_name)

        if method_name is None or not hasattr(source, method_name):
            return {"timestamp_utc": timestamp_utc, "status": "unsupported_source"}

        try:
            return getattr(source, method_name)(latitude, longitude, timestamp_utc)
        except Exception as exc:  # pragma: no cover - defensive path
            return {"timestamp_utc": timestamp_utc, "status": "reader_error", "error": str(exc)}

    def _source_summary(self, name: str, source: Any, latitude: float, longitude: float, timestamps: list[str]) -> dict[str, Any]:
        latest_available = self._source_latest_timestamp(source)
        summary = {
            "latest_available": latest_available,
            "available_timestamps": self._all_source_timestamps(source),
            "records": [],
            "status": "ok" if latest_available is not None else "missing_data",
        }

        if latest_available is None:
            return summary

        for timestamp_utc in timestamps:
            summary["records"].append(
                self._record_for_source(source, name, latitude, longitude, timestamp_utc)
            )
        return summary

    def get_environment_history(
        self,
        latitude: float,
        longitude: float,
        requested_time_utc: str | datetime,
        history_length: int | None = None,
    ) -> dict[str, Any]:
        requested_time = self._normalize_utc(requested_time_utc)
        effective_history_length = self.history_length if history_length is None else max(1, int(history_length))

        source_names = ("nsidc", "era5", "copernicus")
        source_latest_times = {
            name: self._source_latest_timestamp(getattr(self, f"{name}_reader"))
            for name in source_names
        }
        missing_sources = [name for name, value in source_latest_times.items() if value is None]

        result: dict[str, Any] = {
            "requested_time": requested_time,
            "effective_time": None,
            "history_start": None,
            "history_end": None,
            "timestamps": [],
            "complete": False,
            "status": "missing_source_data",
            "source_latest_times": source_latest_times,
            "missing_sources": missing_sources,
            "sources": {},
        }

        if missing_sources:
            for name in source_names:
                result["sources"][name] = self._source_summary(
                    name,
                    getattr(self, f"{name}_reader"),
                    latitude,
                    longitude,
                    [],
                )
            return result

        effective_time = min(source_latest_times[name] for name in source_names)
        effective_dt = self._parse_utc(effective_time)
        requested_dt = self._parse_utc(requested_time)

        available_sets = {
            name: self._normalize_timestamp_set(self._all_source_timestamps(getattr(self, f"{name}_reader")))
            for name in source_names
        }
        common_timestamps = sorted(
            set.intersection(*[available_sets[name] for name in source_names]),
            key=lambda value: self._parse_utc(value),
        )

        available_until_effective = [timestamp for timestamp in common_timestamps if self._parse_utc(timestamp) <= effective_dt]
        if available_until_effective:
            timestamps = available_until_effective[-effective_history_length:]
        else:
            timestamps = []

        complete = len(timestamps) >= effective_history_length
        history_start = timestamps[0] if timestamps else None
        history_end = timestamps[-1] if timestamps else None

        result["effective_time"] = effective_time
        result["history_start"] = history_start
        result["history_end"] = history_end
        result["timestamps"] = timestamps
        result["source_latest_times"] = source_latest_times
        result["complete"] = complete

        if requested_dt > effective_dt:
            result["status"] = "requested_time_after_effective_time"
        elif complete:
            result["status"] = "history_complete"
        else:
            result["status"] = "incomplete_history"

        for name in source_names:
            result["sources"][name] = self._source_summary(
                name,
                getattr(self, f"{name}_reader"),
                latitude,
                longitude,
                timestamps,
            )

        return result
