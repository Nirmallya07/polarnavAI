from flask import Blueprint, jsonify, request

from backend.services.route_optimizer import RouteOptimizer

bp = Blueprint("navigation", __name__, url_prefix="/api")


@bp.post("/navigation/recommend")
def recommend_navigation() -> tuple:
    payload = request.get_json(silent=True) or {}
    start = payload.get("start", {"latitude": -64.2, "longitude": 39.5})
    destination = payload.get("destination", {"latitude": -67.0, "longitude": 50.0})
    vessel = payload.get("vessel", {"speed_knots": 12})
    route_result = RouteOptimizer.optimize_route(
        start=start,
        destination=destination,
        departure_time_utc=payload.get("departure_time_utc", "2026-09-12T08:00:00Z"),
        vessel=vessel,
        mode=payload.get("navigation_mode", "BALANCED"),
    )
    return jsonify({
        "status": "ok",
        "message": "Route recommendation generated from the current time-aware decision-support layer.",
        "recommendation": route_result,
    }), 200
