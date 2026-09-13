from __future__ import annotations

import math

import pandas as pd

from backend.services.era5_reader import ERA5WeatherReader


def _write_era5_file(path, rows):
    df = pd.DataFrame(rows)
    df.to_parquet(path, index=False)


def test_era5_temperature_conversion_and_pressure_conversion(tmp_path) -> None:
    file_path = tmp_path / "weather_antarctic_2023_01_daily.parquet"
    _write_era5_file(
        file_path,
        [{
            "timestamp_utc": "2023-01-01T00:00:00Z",
            "latitude": -64.0,
            "longitude": 0.0,
            "wind_u10_mean": 3.0,
            "wind_v10_mean": 4.0,
            "wind_speed_mean": 5.0,
            "air_temperature_c_mean": 250.0,
            "mean_sea_level_pressure_hpa_mean": 101325.0,
        }],
    )

    reader = ERA5WeatherReader(data_dir=str(tmp_path))
    point = reader.get_weather_point(latitude=-64.0, longitude=0.0, timestamp_utc="2023-01-01T00:00:00Z")

    assert point["air_temperature"] == -23.15
    assert point["pressure"] == 1013.25
    assert point["wind_speed"] == 5.0


def test_era5_wind_speed_and_longitude_normalization(tmp_path) -> None:
    file_path = tmp_path / "weather_antarctic_2023_02_daily.parquet"
    _write_era5_file(
        file_path,
        [{
            "timestamp_utc": "2023-02-01T00:00:00Z",
            "latitude": -64.0,
            "longitude": -179.0,
            "wind_u10_mean": 3.0,
            "wind_v10_mean": 4.0,
            "wind_speed_mean": 5.0,
            "air_temperature_c_mean": -10.0,
            "mean_sea_level_pressure_hpa_mean": 1000.0,
        }],
    )

    reader = ERA5WeatherReader(data_dir=str(tmp_path))
    point = reader.get_weather_point(latitude=-64.0, longitude=181.0, timestamp_utc="2023-02-01T00:00:00Z")

    assert point["wind_u10"] == 3.0
    assert point["wind_v10"] == 4.0
    assert math.isclose(point["wind_speed"], 5.0, rel_tol=1e-9)
    assert point["longitude"] == -179.0


def test_era5_extracts_required_weather_fields(tmp_path) -> None:
    file_path = tmp_path / "weather_antarctic_2023_03_daily.parquet"
    _write_era5_file(
        file_path,
        [{
            "timestamp_utc": "2023-03-01T00:00:00Z",
            "latitude": -60.0,
            "longitude": 10.0,
            "wind_u10_mean": 2.5,
            "wind_v10_mean": -1.0,
            "wind_speed_mean": 2.692582403567252,
            "air_temperature_c_mean": -5.5,
            "mean_sea_level_pressure_hpa_mean": 987.2,
        }],
    )

    reader = ERA5WeatherReader(data_dir=str(tmp_path))
    point = reader.get_weather_point(latitude=-60.0, longitude=10.0, timestamp_utc="2023-03-01T00:00:00Z")

    assert set(point) >= {"wind_u10", "wind_v10", "wind_speed", "air_temperature", "pressure"}
    assert point["wind_u10"] == 2.5
    assert point["wind_v10"] == -1.0
    assert math.isclose(point["wind_speed"], 2.692582403567252, rel_tol=1e-9)
    assert point["air_temperature"] == -5.5
    assert point["pressure"] == 987.2


def test_era5_missing_data_is_reported_safely(tmp_path) -> None:
    file_path = tmp_path / "weather_antarctic_2023_04_daily.parquet"
    _write_era5_file(
        file_path,
        [{
            "timestamp_utc": "2023-04-01T00:00:00Z",
            "latitude": -64.0,
            "longitude": 0.0,
            "wind_u10_mean": None,
            "wind_v10_mean": 2.0,
            "wind_speed_mean": None,
            "air_temperature_c_mean": None,
            "mean_sea_level_pressure_hpa_mean": 995.0,
        }],
    )

    reader = ERA5WeatherReader(data_dir=str(tmp_path))
    point = reader.get_weather_point(latitude=-64.0, longitude=0.0, timestamp_utc="2023-04-01T00:00:00Z")

    assert point["wind_u10"] is None
    assert point["wind_v10"] == 2.0
    assert point["wind_speed"] is None
    assert point["air_temperature"] is None
    assert point["pressure"] == 995.0


def test_era5_timestamp_handling_rejects_unavailable_dates(tmp_path) -> None:
    file_path = tmp_path / "weather_antarctic_2023_05_daily.parquet"
    _write_era5_file(
        file_path,
        [{
            "timestamp_utc": "2023-05-01T00:00:00Z",
            "latitude": -64.0,
            "longitude": 0.0,
            "wind_u10_mean": 1.0,
            "wind_v10_mean": 1.0,
            "wind_speed_mean": 1.4142135623730951,
            "air_temperature_c_mean": 0.0,
            "mean_sea_level_pressure_hpa_mean": 1000.0,
        }],
    )

    reader = ERA5WeatherReader(data_dir=str(tmp_path))
    point = reader.get_weather_point(latitude=-64.0, longitude=0.0, timestamp_utc="2024-01-01T00:00:00Z")

    assert point["error"] == "timestamp_not_available"
