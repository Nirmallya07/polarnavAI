from flask import Blueprint, jsonify

bp = Blueprint("environment", __name__, url_prefix="/api")


@bp.get("/environment")
def get_environment() -> tuple:
    return jsonify({
        "status": "not_implemented",
        "message": "Environment endpoint is not implemented yet.",
        "data": []
    }), 200
