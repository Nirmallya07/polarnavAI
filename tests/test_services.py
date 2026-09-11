from backend.services.data_service import DataService
from backend.services.risk_engine import RiskEngine
from backend.services.route_optimizer import RouteOptimizer


def test_data_service_health() -> None:
    assert DataService.health_check()["status"] == "ok"


def test_risk_engine_placeholder() -> None:
    result = RiskEngine.evaluate_risk()
    assert result["status"] == "not_implemented"


def test_route_optimizer_placeholder() -> None:
    result = RouteOptimizer.optimize_route(mode="SAFE")
    assert result["status"] == "not_implemented"
