import sys

from flask import Blueprint, jsonify, request

sys.path.insert(0, "/mnt/polarnav-models")

from sea_ice_project_module.inference import predict_sea_ice

from backend.services.environment_history_coordinator import EnvironmentalHistoryCoordinator
from backend.services.patch_assembler import SeaIcePatchAssembler

bp = Blueprint("predictions", __name__, url_prefix="/api")


@bp.get("/predictions/sea-ice")
def get_sea_ice_predictions() -> tuple:
    latitude = float(request.args.get("latitude", "-64.0"))
    longitude = float(request.args.get("longitude", "12.0"))
    timestamp_utc = request.args.get("timestamp_utc") or EnvironmentalHistoryCoordinator()._source_latest_timestamp(
        EnvironmentalHistoryCoordinator().nsidc_reader
    ) or "2023-12-31T00:00:00Z"

    coordinator = EnvironmentalHistoryCoordinator()
    history = coordinator.get_environment_history(latitude=latitude, longitude=longitude, requested_time_utc=timestamp_utc)
    if history.get("status") != "history_complete":
        return jsonify({
            "status": "error",
            "message": "Unable to build real environmental history.",
            "data": [],
        }), 500

    assembler = SeaIcePatchAssembler()
    tensor = assembler.build_model_input(latitude, longitude, history["timestamps"])
    forecast = predict_sea_ice(tensor)

    summary = []
    for day_index in range(forecast.shape[0]):
        sic_map = forecast[day_index]
        summary.append({
            "forecast_day": day_index + 1,
            "min_sic": float(sic_map.min()),
            "max_sic": float(sic_map.max()),
            "mean_sic": float(sic_map.mean()),
        })

    return jsonify({
        "status": "ok",
        "effective_timestamp": timestamp_utc,
        "timestamps_used": history.get("timestamps", []),
        "input_shape": list(tensor.shape),
        "output_shape": list(forecast.shape),
        "channel_order": [
            "SIC",
            "wind_u10",
            "wind_v10",
            "wind_speed",
            "air_temperature",
            "pressure",
            "ocean_u",
            "ocean_v",
            "SST",
        ],
        "data": summary,
    }), 200


@bp.get("/predictions/icebergs")
def get_iceberg_predictions() -> tuple:
    return jsonify({
        "status": "not_implemented",
        "message": "Iceberg prediction endpoint is not implemented yet.",
        "data": []
    }), 200
