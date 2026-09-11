from flask.testing import FlaskClient

from backend.app import app


def test_health_endpoint() -> None:
    client: FlaskClient = app.test_client()
    response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ok"
    assert payload["service"] == "polarnav-backend"
