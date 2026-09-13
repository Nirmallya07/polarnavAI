from __future__ import annotations

from datetime import datetime, timedelta, timezone

from backend.services.environment_history_coordinator import EnvironmentalHistoryCoordinator


class StubSource:
    def __init__(self, timestamps):
        self._timestamps = sorted(timestamps)

    def list_available_timestamps(self):
        return self._timestamps

    def latest_available_timestamp(self):
        return self._timestamps[-1] if self._timestamps else None

    def get_point(self, latitude, longitude, timestamp_utc):
        return {"timestamp_utc": timestamp_utc, "latitude": latitude, "longitude": longitude}


def _make_source_with_window(start_utc: str, end_utc: str):
    start = datetime.strptime(start_utc, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    end = datetime.strptime(end_utc, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    values = []
    current = start
    while current <= end:
        values.append(current.strftime("%Y-%m-%dT%H:%M:%SZ"))
        current += timedelta(days=1)
    return StubSource(values)


def test_coordinator_accepts_matching_history_for_all_sources():
    source_window = "2026-08-29T00:00:00Z"
    end_window = "2026-09-12T00:00:00Z"
    coordinator = EnvironmentalHistoryCoordinator(
        nsidc_reader=_make_source_with_window(source_window, end_window),
        era5_reader=_make_source_with_window(source_window, end_window),
        copernicus_reader=_make_source_with_window(source_window, end_window),
    )

    result = coordinator.get_environment_history(
        latitude=-64.0,
        longitude=12.0,
        requested_time_utc="2026-09-12T00:00:00Z",
    )

    assert result["effective_time"] == "2026-09-12T00:00:00Z"
    assert result["complete"] is True
    assert result["status"] == "history_complete"
    assert len(result["timestamps"]) == 15
    assert result["timestamps"][0] == "2026-08-29T00:00:00Z"
    assert result["timestamps"][-1] == "2026-09-12T00:00:00Z"


def test_coordinator_uses_common_latest_timestamp_when_sources_differ():
    coordinator = EnvironmentalHistoryCoordinator(
        nsidc_reader=_make_source_with_window("2026-08-29T00:00:00Z", "2026-09-12T00:00:00Z"),
        era5_reader=_make_source_with_window("2026-08-29T00:00:00Z", "2026-09-11T00:00:00Z"),
        copernicus_reader=_make_source_with_window("2026-08-29T00:00:00Z", "2026-09-10T00:00:00Z"),
    )

    result = coordinator.get_environment_history(
        latitude=-64.0,
        longitude=12.0,
        requested_time_utc="2026-09-12T00:00:00Z",
    )

    assert result["effective_time"] == "2026-09-10T00:00:00Z"
    assert result["complete"] is False
    assert result["status"] == "requested_time_after_effective_time"
    assert result["source_latest_times"]["nsidc"] == "2026-09-12T00:00:00Z"
    assert result["source_latest_times"]["era5"] == "2026-09-11T00:00:00Z"
    assert result["source_latest_times"]["copernicus"] == "2026-09-10T00:00:00Z"


def test_coordinator_reports_when_requested_time_is_newer_than_available_data():
    coordinator = EnvironmentalHistoryCoordinator(
        nsidc_reader=_make_source_with_window("2026-08-29T00:00:00Z", "2026-09-12T00:00:00Z"),
        era5_reader=_make_source_with_window("2026-08-29T00:00:00Z", "2026-09-12T00:00:00Z"),
        copernicus_reader=_make_source_with_window("2026-08-29T00:00:00Z", "2026-09-12T00:00:00Z"),
    )

    result = coordinator.get_environment_history(
        latitude=-64.0,
        longitude=12.0,
        requested_time_utc="2026-09-15T12:00:00Z",
    )

    assert result["requested_time"] == "2026-09-15T12:00:00Z"
    assert result["effective_time"] == "2026-09-12T00:00:00Z"
    assert result["status"] == "requested_time_after_effective_time"
    assert result["complete"] is True


def test_coordinator_reports_missing_source_data():
    coordinator = EnvironmentalHistoryCoordinator(
        nsidc_reader=StubSource([]),
        era5_reader=_make_source_with_window("2026-09-01T00:00:00Z", "2026-09-12T00:00:00Z"),
        copernicus_reader=_make_source_with_window("2026-09-01T00:00:00Z", "2026-09-12T00:00:00Z"),
    )

    result = coordinator.get_environment_history(
        latitude=-64.0,
        longitude=12.0,
        requested_time_utc="2026-09-12T00:00:00Z",
    )

    assert result["effective_time"] is None
    assert result["complete"] is False
    assert "nsidc" in result["missing_sources"]
    assert result["status"] == "missing_source_data"


def test_coordinator_marks_history_incomplete_when_fewer_than_15_timesteps_exist():
    coordinator = EnvironmentalHistoryCoordinator(
        nsidc_reader=_make_source_with_window("2026-09-01T00:00:00Z", "2026-09-08T00:00:00Z"),
        era5_reader=_make_source_with_window("2026-09-01T00:00:00Z", "2026-09-08T00:00:00Z"),
        copernicus_reader=_make_source_with_window("2026-09-01T00:00:00Z", "2026-09-08T00:00:00Z"),
    )

    result = coordinator.get_environment_history(
        latitude=-64.0,
        longitude=12.0,
        requested_time_utc="2026-09-08T00:00:00Z",
    )

    assert result["effective_time"] == "2026-09-08T00:00:00Z"
    assert result["complete"] is False
    assert result["status"] == "incomplete_history"
    assert len(result["timestamps"]) == 8


def test_coordinator_uses_exactly_15_valid_timesteps():
    source_window_start = "2026-08-29T00:00:00Z"
    source_window_end = "2026-09-12T00:00:00Z"
    coordinator = EnvironmentalHistoryCoordinator(
        nsidc_reader=_make_source_with_window(source_window_start, source_window_end),
        era5_reader=_make_source_with_window(source_window_start, source_window_end),
        copernicus_reader=_make_source_with_window(source_window_start, source_window_end),
    )

    result = coordinator.get_environment_history(
        latitude=-64.0,
        longitude=12.0,
        requested_time_utc="2026-09-12T00:00:00Z",
    )

    assert result["complete"] is True
    assert len(result["timestamps"]) == 15
    assert result["timestamps"][0] == "2026-08-29T00:00:00Z"
    assert result["timestamps"][-1] == "2026-09-12T00:00:00Z"


def test_coordinator_normalizes_utc_inputs():
    coordinator = EnvironmentalHistoryCoordinator(
        nsidc_reader=_make_source_with_window("2026-09-01T00:00:00Z", "2026-09-12T00:00:00Z"),
        era5_reader=_make_source_with_window("2026-09-01T00:00:00Z", "2026-09-12T00:00:00Z"),
        copernicus_reader=_make_source_with_window("2026-09-01T00:00:00Z", "2026-09-12T00:00:00Z"),
    )

    result = coordinator.get_environment_history(
        latitude=-64.0,
        longitude=12.0,
        requested_time_utc="2026-09-12T12:00:00+00:00",
    )

    assert result["requested_time"] == "2026-09-12T12:00:00Z"
    assert result["effective_time"] == "2026-09-12T00:00:00Z"


def test_coordinator_does_not_silently_fallback_to_2023_when_newer_data_requested():
    coordinator = EnvironmentalHistoryCoordinator(
        nsidc_reader=_make_source_with_window("2023-09-01T00:00:00Z", "2023-09-12T00:00:00Z"),
        era5_reader=_make_source_with_window("2023-09-01T00:00:00Z", "2023-09-12T00:00:00Z"),
        copernicus_reader=_make_source_with_window("2023-09-01T00:00:00Z", "2023-09-12T00:00:00Z"),
    )

    result = coordinator.get_environment_history(
        latitude=-64.0,
        longitude=12.0,
        requested_time_utc="2026-09-13T12:00:00Z",
    )

    assert result["requested_time"] == "2026-09-13T12:00:00Z"
    assert result["effective_time"] == "2023-09-12T00:00:00Z"
    assert result["status"] == "requested_time_after_effective_time"
    assert "2023-09-12T00:00:00Z" in str(result["source_latest_times"])
