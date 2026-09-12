from __future__ import annotations

import numpy as np
import xarray as xr

from backend.services.copernicus_reader import CopernicusReader


def _write_monthly_dataset(path, *, lat_values, lon_values, time_values, uo_values, vo_values):
    ds = xr.Dataset(
        {
            "uo": (("time", "lat", "lon"), np.asarray(uo_values, dtype=float)),
            "vo": (("time", "lat", "lon"), np.asarray(vo_values, dtype=float)),
            "valid_ocean_mask": (("time", "lat", "lon"), np.ones((len(time_values), len(lat_values), len(lon_values)), dtype=int)),
        },
        coords={
            "time": np.asarray(time_values, dtype="datetime64[ns]"),
            "lat": np.asarray(lat_values, dtype=float),
            "lon": np.asarray(lon_values, dtype=float),
        },
    )
    ds.to_netcdf(path)


def test_resolve_january_file_for_timestamp(tmp_path):
    expected = tmp_path / "cmems_mod_glo_phy_my_0.083deg_P1D-m_uo-vo-thetao-sithick-usi-vsi_180.00W-180.00E_75.00S-45.00S_0.49m_2023-01-01T00-00-00-2023-01-31T00-00-00.nc"
    expected.touch()

    reader = CopernicusReader(data_dir=str(tmp_path))

    assert reader.resolve_file_for_timestamp("2023-01-15T12:00:00Z") == expected


def test_resolve_february_file_for_timestamp(tmp_path):
    expected = tmp_path / "cmems_mod_glo_phy_my_0.083deg_P1D-m_uo-vo-thetao-sithick-usi-vsi_180.00W-180.00E_75.00S-45.00S_0.49m_2023-02-01T00-00-00-2023-02-28T00-00-00.nc"
    expected.touch()

    reader = CopernicusReader(data_dir=str(tmp_path))

    assert reader.resolve_file_for_timestamp("2023-02-10T06:00:00Z") == expected


def test_get_ocean_point_maps_uo_vo_and_handles_nan(tmp_path):
    lat_values = [-65.0, -64.0, -63.0]
    lon_values = [19.0, 20.0, 21.0]
    time_values = ["2023-01-15T00:00:00", "2023-01-15T12:00:00"]
    uo_values = np.array([
        [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, 0.9]],
        [[1.1, 1.2, 1.3], [1.4, 1.5, 1.6], [1.7, 1.8, 1.9]],
    ])
    vo_values = np.array([
        [[0.11, 0.12, 0.13], [0.14, 0.15, 0.16], [0.17, 0.18, 0.19]],
        [[1.11, 1.12, 1.13], [1.14, 1.15, 1.16], [1.17, 1.18, 1.19]],
    ])
    file_path = tmp_path / "cmems_mod_glo_phy_my_0.083deg_P1D-m_uo-vo-thetao-sithick-usi-vsi_180.00W-180.00E_75.00S-45.00S_0.49m_2023-01-01T00-00-00-2023-01-31T00-00-00.nc"
    _write_monthly_dataset(file_path, lat_values=lat_values, lon_values=lon_values, time_values=time_values, uo_values=uo_values, vo_values=vo_values)

    reader = CopernicusReader(data_dir=str(tmp_path))

    point = reader.get_ocean_point(-64.0, 20.0, "2023-01-15T12:00:00Z")

    assert point["ocean_u"] == 1.5
    assert point["ocean_v"] == 1.15


def test_get_ocean_point_returns_none_for_nan_values(tmp_path):
    lat_values = [-64.0]
    lon_values = [20.0]
    time_values = ["2023-01-15T12:00:00"]
    uo_values = np.array([[[np.nan]]])
    vo_values = np.array([[[np.nan]]])
    file_path = tmp_path / "cmems_mod_glo_phy_my_0.083deg_P1D-m_uo-vo-thetao-sithick-usi-vsi_180.00W-180.00E_75.00S-45.00S_0.49m_2023-01-01T00-00-00-2023-01-31T00-00-00.nc"
    _write_monthly_dataset(file_path, lat_values=lat_values, lon_values=lon_values, time_values=time_values, uo_values=uo_values, vo_values=vo_values)

    reader = CopernicusReader(data_dir=str(tmp_path))

    point = reader.get_ocean_point(-64.0, 20.0, "2023-01-15T12:00:00Z")

    assert point["ocean_u"] is None
    assert point["ocean_v"] is None


def test_missing_file_raises_file_not_found(tmp_path):
    reader = CopernicusReader(data_dir=str(tmp_path))

    try:
        reader.resolve_file_for_timestamp("2023-03-15T12:00:00Z")
        assert False, "Expected FileNotFoundError"
    except FileNotFoundError:
        pass


def test_out_of_domain_coordinates_return_none(tmp_path):
    file_path = tmp_path / "cmems_mod_glo_phy_my_0.083deg_P1D-m_uo-vo-thetao-sithick-usi-vsi_180.00W-180.00E_75.00S-45.00S_0.49m_2023-01-01T00-00-00-2023-01-31T00-00-00.nc"
    lat_values = [-64.0]
    lon_values = [20.0]
    time_values = ["2023-01-15T12:00:00"]
    uo_values = np.array([[[0.5]]])
    vo_values = np.array([[[0.6]]])
    _write_monthly_dataset(file_path, lat_values=lat_values, lon_values=lon_values, time_values=time_values, uo_values=uo_values, vo_values=vo_values)

    reader = CopernicusReader(data_dir=str(tmp_path))

    point = reader.get_ocean_point(-80.0, 20.0, "2023-01-15T12:00:00Z")
    assert point["ocean_u"] is None
    assert point["ocean_v"] is None


def test_malformed_timestamp_raises_value_error(tmp_path):
    reader = CopernicusReader(data_dir=str(tmp_path))

    try:
        reader.resolve_file_for_timestamp("not-a-timestamp")
        assert False, "Expected ValueError"
    except ValueError:
        pass
