from flask import Blueprint, jsonify, request

from backend.services.data_service import DataService

bp = Blueprint("environment", __name__, url_prefix="/api")


@bp.get("/environment")
def get_environment() -> tuple:
    latitude = float(request.args.get("latitude", "-64.2"))
    longitude = float(request.args.get("longitude", "39.5"))
    timestamp_utc = request.args.get("timestamp_utc", "2026-09-12T08:00:00Z")
    return jsonify(DataService.get_environment(latitude, longitude, timestamp_utc)), 200
