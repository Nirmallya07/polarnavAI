from flask import Blueprint, jsonify

bp = Blueprint("predictions", __name__, url_prefix="/api")


@bp.get("/predictions/sea-ice")
def get_sea_ice_predictions() -> tuple:
    return jsonify({
        "status": "not_implemented",
        "message": "Sea-ice prediction endpoint is not implemented yet.",
        "data": []
    }), 200


@bp.get("/predictions/icebergs")
def get_iceberg_predictions() -> tuple:
    return jsonify({
        "status": "not_implemented",
        "message": "Iceberg prediction endpoint is not implemented yet.",
        "data": []
    }), 200
