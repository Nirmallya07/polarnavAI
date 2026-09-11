from flask import Blueprint, jsonify, request

bp = Blueprint("navigation", __name__, url_prefix="/api")


@bp.post("/navigation/recommend")
def recommend_navigation() -> tuple:
    payload = request.get_json(silent=True) or {}
    return jsonify({
        "status": "not_implemented",
        "message": "Navigation recommendation endpoint is not implemented yet.",
        "received": payload,
    }), 200
