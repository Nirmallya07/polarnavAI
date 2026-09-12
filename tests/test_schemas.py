import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS_DIR = ROOT / "contracts"


def load_schema(name: str):
    with (CONTRACTS_DIR / name).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def assert_valid(schema_name: str, payload: dict) -> None:
    validator = Draft202012Validator(load_schema(schema_name))
    validator.validate(payload)


def assert_invalid(schema_name: str, payload: dict) -> None:
    validator = Draft202012Validator(load_schema(schema_name))
    with pytest.raises(ValidationError):
        validator.validate(payload)


def test_navigation_request_valid_schema() -> None:
    payload = {
        "start": {"latitude": -64.2, "longitude": 39.5},
        "destination": {"latitude": -67.0, "longitude": 50.0},
        "departure_time_utc": "2026-09-12T06:00:00Z",
        "vessel": {"type": "research_vessel", "speed_knots": 12, "fuel_rate": 85},
        "navigation_mode": "BALANCED",
    }
    assert_valid("navigation_request.schema.json", payload)


def test_navigation_request_invalid_latitude_fails() -> None:
    payload = {
        "start": {"latitude": -90.1, "longitude": 39.5},
        "destination": {"latitude": -67.0, "longitude": 50.0},
        "departure_time_utc": "2026-09-12T06:00:00Z",
        "vessel": {"type": "research_vessel", "speed_knots": 12, "fuel_rate": 85},
        "navigation_mode": "BALANCED",
    }
    assert_invalid("navigation_request.schema.json", payload)


def test_navigation_request_invalid_longitude_fails() -> None:
    payload = {
        "start": {"latitude": -64.2, "longitude": 180.1},
        "destination": {"latitude": -67.0, "longitude": 50.0},
        "departure_time_utc": "2026-09-12T06:00:00Z",
        "vessel": {"type": "research_vessel", "speed_knots": 12, "fuel_rate": 85},
        "navigation_mode": "BALANCED",
    }
    assert_invalid("navigation_request.schema.json", payload)


def test_navigation_request_invalid_navigation_mode_fails() -> None:
    payload = {
        "start": {"latitude": -64.2, "longitude": 39.5},
        "destination": {"latitude": -67.0, "longitude": 50.0},
        "departure_time_utc": "2026-09-12T06:00:00Z",
        "vessel": {"type": "research_vessel", "speed_knots": 12, "fuel_rate": 85},
        "navigation_mode": "INVALID",
    }
    assert_invalid("navigation_request.schema.json", payload)


def test_navigation_request_invalid_fuel_rate_fails() -> None:
    payload = {
        "start": {"latitude": -64.2, "longitude": 39.5},
        "destination": {"latitude": -67.0, "longitude": 50.0},
        "departure_time_utc": "2026-09-12T06:00:00Z",
        "vessel": {"type": "research_vessel", "speed_knots": 12, "fuel_rate": 0},
        "navigation_mode": "BALANCED",
    }
    assert_invalid("navigation_request.schema.json", payload)


def test_sea_ice_prediction_valid_schema() -> None:
    payload = {
        "model": "sea_ice_baseline_v1",
        "forecast_time_utc": "2026-09-11T18:00:00Z",
        "horizon_hours": 12,
        "grid": [
            {"latitude": -64.25, "longitude": 40.5, "predicted_concentration": 0.72},
            {"latitude": -64.5, "longitude": 41.0, "predicted_concentration": 0.65},
        ],
    }
    assert_valid("sea_ice_prediction.schema.json", payload)


def test_sea_ice_prediction_concentration_gt_1_fails() -> None:
    payload = {
        "model": "sea_ice_baseline_v1",
        "forecast_time_utc": "2026-09-11T18:00:00Z",
        "horizon_hours": 12,
        "grid": [{"latitude": -64.25, "longitude": 40.5, "predicted_concentration": 1.5}],
    }
    assert_invalid("sea_ice_prediction.schema.json", payload)


def test_iceberg_prediction_valid_schema() -> None:
    payload = {
        "model": "iceberg_velocity_v1",
        "generated_at_utc": "2026-09-11T06:00:00Z",
        "tracks": [
            {
                "iceberg_id": "A12345",
                "predictions": [
                    {"timestamp_utc": "2026-09-11T12:00:00Z", "latitude": -61.2, "longitude": -45.8},
                    {"timestamp_utc": "2026-09-11T18:00:00Z", "latitude": -61.3, "longitude": -45.6},
                ],
                "uncertainty_km": 15.0,
            }
        ],
    }
    assert_valid("iceberg_prediction.schema.json", payload)


def test_iceberg_prediction_negative_uncertainty_fails() -> None:
    payload = {
        "model": "iceberg_velocity_v1",
        "generated_at_utc": "2026-09-11T06:00:00Z",
        "tracks": [
            {
                "iceberg_id": "A12345",
                "predictions": [{"timestamp_utc": "2026-09-11T12:00:00Z", "latitude": -61.2, "longitude": -45.8}],
                "uncertainty_km": -1.0,
            }
        ],
    }
    assert_invalid("iceberg_prediction.schema.json", payload)


def test_environment_response_valid_schema() -> None:
    payload = {
        "timestamp_utc": "2026-09-11T18:00:00Z",
        "latitude": -64.25,
        "longitude": 40.5,
        "sea_ice_concentration": 0.72,
        "wind_u10": None,
        "wind_v10": None,
        "air_temperature": None,
        "ocean_u": None,
        "ocean_v": None,
        "wave_height": None,
        "wave_period": None,
    }
    assert_valid("environment.schema.json", payload)


def test_risk_response_valid_schema() -> None:
    payload = {
        "timestamp_utc": "2026-09-11T18:00:00Z",
        "latitude": -64.2,
        "longitude": 40.5,
        "risk_score": 67,
        "risk_level": "HIGH",
        "components": {"sea_ice": 55, "iceberg": 80, "weather": 40, "ocean": 25},
    }
    assert_valid("risk.schema.json", payload)


def test_risk_score_above_100_fails() -> None:
    payload = {
        "timestamp_utc": "2026-09-11T18:00:00Z",
        "latitude": -64.2,
        "longitude": 40.5,
        "risk_score": 101,
        "risk_level": "CRITICAL",
        "components": {"sea_ice": 55, "iceberg": 80, "weather": 40, "ocean": 25},
    }
    assert_invalid("risk.schema.json", payload)


def test_route_response_valid_schema() -> None:
    payload = {
        "mode": "BALANCED",
        "route": [
            {
                "latitude": -64.2,
                "longitude": 39.5,
                "arrival_time_utc": "2026-09-12T06:00:00Z",
                "risk_score": 18,
                "risk_level": "LOW",
                "eta_hours": 0,
            },
            {
                "latitude": -64.7,
                "longitude": 41.2,
                "arrival_time_utc": "2026-09-12T10:12:00Z",
                "risk_score": 31,
                "risk_level": "MODERATE",
                "eta_hours": 4.2,
            },
        ],
        "risk_score": 28,
        "distance_km": 550,
        "eta_hours": 14.5,
        "fuel_estimate": 1240,
        "cost_score": 2840.5,
    }
    assert_valid("route.schema.json", payload)
