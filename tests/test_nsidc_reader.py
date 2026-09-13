from __future__ import annotations

import numpy as np
import xarray as xr

from backend.services.nsidc_reader import NSIDCSeaIceReader
from backend.services.data_service import DataService


def _write_test_nsidc_file(path, concentration_values):
    times = np.array(["2024-01-01T00:00:00", "2024-01-02T00:00:00"], dtype="datetime64[ns]")
    y = np.array([-64.0, -65.0], dtype=np.float32)
    x = np.array([0.0, 1.0], dtype=np.float32)
    lat = np.array([[y[0], y[0]], [y[1], y[1]]], dtype=np.float32)
    lon = np.array([[x[0], x[1]], [x[0], x[1]]], dtype=np.float32)

    data = np.asarray(concentration_values, dtype=np.float32)
    dataset = xr.Dataset(
        {
            "cdr_sea_ice_concentration": (("time", "y", "x"), data),
        },
        coords={
            "time": times,
            "y": y,
            "x": x,
            "latitude": (("y", "x"), lat),
            "longitude": (("y", "x"), lon),
        },
    )
    dataset.to_netcdf(path)


def test_nsidc_reader_reads_sea_ice_concentration_from_daily_file(tmp_path) -> None:
    file_path = tmp_path / "NSIDC_G02202_V6_20240101.nc"
    _write_test_nsidc_file(
        file_path,
        [
            [[10.0, 30.0], [50.0, 70.0]],
            [[15.0, 35.0], [55.0, 75.0]],
        ],
    )

    reader = NSIDCSeaIceReader(data_dir=str(tmp_path))

    point = reader.get_sea_ice_point(latitude=-64.9, longitude=0.9, timestamp_utc="2024-01-02T12:00:00Z")

    assert point["source"] == "nsidc"
    assert point["sea_ice_concentration"] == 0.75


def test_data_service_uses_nsidc_sea_ice_value(monkeypatch) -> None:
    class DummyReader:
        def get_sea_ice_point(self, latitude, longitude, timestamp_utc):
            return {
                "timestamp_utc": timestamp_utc,
                "latitude": latitude,
                "longitude": longitude,
                "sea_ice_concentration": 0.63,
                "source": "nsidc",
            }

    monkeypatch.setattr(DataService, "_nsidc_reader", DummyReader())

    state = DataService.get_environment(latitude=-64.5, longitude=0.0, timestamp_utc="2024-01-02T12:00:00Z")

    assert state["sea_ice_concentration"] == 0.63
    assert state["source"] == "nsidc"
