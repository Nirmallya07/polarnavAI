import sys

from flask import Blueprint, jsonify, request

sys.path.insert(0, "/mnt/polarnav-models")

from sea_ice_project_module.inference import predict_sea_ice

from backend.services.data_service import DataService
from backend.services.environment_history_coordinator import EnvironmentalHistoryCoordinator
from backend.services.patch_assembler import SeaIcePatchAssembler
from backend.services.risk_engine import RiskEngine

bp = Blueprint("environment", __name__, url_prefix="/api")


def _latest_common_timestamp() -> str:
    coordinator = EnvironmentalHistoryCoordinator()
    latest_by_source = {
        name: coordinator._source_latest_timestamp(getattr(coordinator, f"{name}_reader"))
        for name in ("nsidc", "era5", "copernicus")
    }
    valid = [value for value in latest_by_source.values() if value is not None]
    if not valid:
        return "2023-12-31T00:00:00Z"
    return min(valid)


def _build_patch_forecast(reference_time: str, center_latitude: float = -64.0, center_longitude: float = 12.0):
    coordinator = EnvironmentalHistoryCoordinator()
    history = coordinator.get_environment_history(
        latitude=center_latitude,
        longitude=center_longitude,
        requested_time_utc=reference_time,
    )
    if history.get("status") != "history_complete":
        raise ValueError(f"Unable to build the environmental history: {history}")

    assembler = SeaIcePatchAssembler()
    tensor = assembler.build_model_input(center_latitude, center_longitude, history["timestamps"])
    forecast = predict_sea_ice(tensor)
    lat_grid, lon_grid = assembler._patch_center_array(center_latitude, center_longitude)
    return history, tensor, forecast, lat_grid, lon_grid


@bp.get("/environment")
def get_environment() -> tuple:
    latitude = float(request.args.get("latitude", "-64.2"))
    longitude = float(request.args.get("longitude", "39.5"))
    timestamp_utc = request.args.get("timestamp_utc", "2026-09-12T08:00:00Z")
    return jsonify(DataService.get_environment(latitude, longitude, timestamp_utc)), 200


@bp.get("/risk/heatmap")
def get_risk_heatmap() -> tuple:
    forecast_key = request.args.get("forecast", "plus3").strip() or "plus3"
    if forecast_key not in {"current", "plus1", "plus2", "plus3", "plus4", "plus5"}:
        forecast_key = "plus3"

    reference_time = request.args.get("as_of_utc") or _latest_common_timestamp()
    center_latitude = float(request.args.get("latitude", "-64.0"))
    center_longitude = float(request.args.get("longitude", "12.0"))

    try:
        history, tensor, forecast, lat_grid, lon_grid = _build_patch_forecast(reference_time, center_latitude, center_longitude)
    except Exception as exc:  # pragma: no cover - fallback when the model cannot be used
        return jsonify({
            "status": "error",
            "forecast_key": forecast_key,
            "reference_time_utc": reference_time,
            "source": "real-data",
            "message": f"Unable to build real forecast patch: {exc}",
            "cells": [],
        }), 500

    day_offset = {"current": 0, "plus1": 0, "plus2": 1, "plus3": 2, "plus4": 3, "plus5": 4}.get(forecast_key, 2)
    day_index = max(0, min(day_offset, forecast.shape[0] - 1))
    sic_map = forecast[day_index]
    points = []

    for row in range(0, sic_map.shape[0], 3):
        for col in range(0, sic_map.shape[1], 3):
            latitude = float(lat_grid[row, col])
            longitude = float(lon_grid[row, col])
            sea_ice_concentration = float(sic_map[row, col])
            environment_state = DataService.get_environment(latitude, longitude, reference_time)
            environment_state["sea_ice_concentration"] = sea_ice_concentration
            risk_result = RiskEngine.evaluate_risk(environment_state)
            points.append({
                "latitude": latitude,
                "longitude": longitude,
                "risk_score": float(risk_result.get("risk_score", 0.0)),
                "risk_level": risk_result.get("risk_level", "LOW"),
                "forecast_day": day_index + 1,
                "timestamp_utc": reference_time,
                "source": "real-data",
            })

    return jsonify({
        "status": "ok",
        "forecast_key": forecast_key,
        "reference_time_utc": reference_time,
        "source": "real-data",
        "effective_timestamp": reference_time,
        "history_timestamps": history.get("timestamps", []),
        "input_shape": list(tensor.shape),
        "forecast_shape": list(forecast.shape),
        "cells": points,
    }), 200
