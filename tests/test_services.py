from backend.services.data_service import DataService
from backend.services.risk_engine import RiskEngine
from backend.services.route_optimizer import RouteOptimizer
from backend.utils.geo import haversine_km


def test_data_service_health() -> None:
    assert DataService.health_check()["status"] == "ok"


def test_risk_engine_returns_time_aware_risk() -> None:
    risk = RiskEngine.evaluate_risk(
        {
            "timestamp_utc": "2026-09-12T10:00:00Z",
            "latitude": -64.2,
            "longitude": 39.5,
            "sea_ice_concentration": 0.75,
            "wind_u10": 12.0,
            "wind_v10": -7.0,
            "air_temperature": -4.0,
            "ocean_u": 0.5,
            "ocean_v": -0.1,
            "wave_height": 2.5,
            "wave_period": 7.0,
        }
    )
    assert 0 <= risk["risk_score"] <= 100
    assert risk["risk_level"] in {"LOW", "MODERATE", "HIGH", "CRITICAL"}
    assert set(risk["components"]).issuperset({"sea_ice", "iceberg", "weather", "ocean"})


def test_route_optimizer_returns_route_for_balanced_mode() -> None:
    route = RouteOptimizer.optimize_route(
        start={"latitude": -64.2, "longitude": 39.5},
        destination={"latitude": -65.0, "longitude": 41.0},
        departure_time_utc="2026-09-12T08:00:00Z",
        vessel={"speed_knots": 12},
        mode="BALANCED",
    )
    assert route["mode"] == "BALANCED"
    assert route["risk_score"] >= 0
    assert route["distance_km"] > 0
    assert len(route["route"]) >= 2
    assert route["route"][0]["latitude"] == -64.2


def test_route_optimizer_is_grid_based_and_time_aware() -> None:
    route = RouteOptimizer.optimize_route(
        start={"latitude": -64.0, "longitude": 38.0},
        destination={"latitude": -64.0, "longitude": 44.0},
        departure_time_utc="2026-09-12T08:00:00Z",
        vessel={"speed_knots": 12},
        mode="BALANCED",
    )

    assert route["route"][0]["latitude"] == -64.0
    assert route["route"][0]["longitude"] == 38.0
    assert route["route"][-1]["latitude"] == -64.0
    assert route["route"][-1]["longitude"] == 44.0
    assert len(route["route"]) > 6

    timestamps = [point["arrival_time_utc"] for point in route["route"]]
    assert len(timestamps) == len(set(timestamps))
    assert timestamps == sorted(timestamps)

    for index in range(1, len(route["route"])):
        previous = route["route"][index - 1]
        current = route["route"][index]
        assert current["risk_score"] >= 0
        assert previous["arrival_time_utc"] < current["arrival_time_utc"]


def test_route_optimizer_avoids_high_risk_band_with_dependency_injection() -> None:
    start = {"latitude": -64.0, "longitude": 38.0}
    destination = {"latitude": -64.0, "longitude": 44.0}
    high_risk_min_lon = 40.5
    high_risk_max_lon = 41.5
    high_risk_latitude_margin = 1.2

    lookup_calls = []

    def custom_environment_lookup(latitude: float, longitude: float, timestamp_utc: str) -> dict:
        lookup_calls.append((float(latitude), float(longitude), timestamp_utc))
        if high_risk_min_lon <= longitude <= high_risk_max_lon and abs(latitude + 64.0) <= high_risk_latitude_margin:
            return {
                "timestamp_utc": timestamp_utc,
                "latitude": float(latitude),
                "longitude": float(longitude),
                "sea_ice_concentration": 0.92,
                "wind_u10": 28.0,
                "wind_v10": -12.0,
                "ocean_u": 1.0,
                "ocean_v": 0.4,
                "wave_height": 5.8,
                "wave_period": 9.0,
            }
        return {
            "timestamp_utc": timestamp_utc,
            "latitude": float(latitude),
            "longitude": float(longitude),
            "sea_ice_concentration": 0.25,
            "wind_u10": 6.0,
            "wind_v10": -2.0,
            "ocean_u": 0.3,
            "ocean_v": -0.1,
            "wave_height": 1.2,
            "wave_period": 6.0,
        }

    def custom_risk_evaluator(environment_state: dict) -> dict:
        if high_risk_min_lon <= environment_state["longitude"] <= high_risk_max_lon and abs(environment_state["latitude"] + 64.0) <= high_risk_latitude_margin:
            return {
                "timestamp_utc": environment_state["timestamp_utc"],
                "latitude": environment_state["latitude"],
                "longitude": environment_state["longitude"],
                "risk_score": 96.0,
                "risk_level": "CRITICAL",
            }
        return {
            "timestamp_utc": environment_state["timestamp_utc"],
            "latitude": environment_state["latitude"],
            "longitude": environment_state["longitude"],
            "risk_score": 12.0,
            "risk_level": "LOW",
        }

    direct_distance = haversine_km(start["latitude"], start["longitude"], destination["latitude"], destination["longitude"])

    route = RouteOptimizer.optimize_route(
        start=start,
        destination=destination,
        departure_time_utc="2026-09-12T08:00:00Z",
        vessel={"speed_knots": 12},
        mode="SAFE",
        environment_lookup=custom_environment_lookup,
        risk_evaluator=custom_risk_evaluator,
    )

    direct_path = [
        {"latitude": start["latitude"], "longitude": start["longitude"]},
        {"latitude": destination["latitude"], "longitude": destination["longitude"]},
    ]
    route_points = route["route"]
    route_points_in_high_risk = [
        point for point in route_points
        if high_risk_min_lon <= point["longitude"] <= high_risk_max_lon and abs(point["latitude"] + 64.0) <= high_risk_latitude_margin
    ]

    assert len(lookup_calls) > 0
    timestamps = {timestamp for _, _, timestamp in lookup_calls}
    assert len(timestamps) > 1
    assert route_points[0]["latitude"] == start["latitude"]
    assert route_points[0]["longitude"] == start["longitude"]
    assert route_points[-1]["latitude"] == destination["latitude"]
    assert route_points[-1]["longitude"] == destination["longitude"]
    assert route_points != [
        {"latitude": start["latitude"], "longitude": start["longitude"]},
        {"latitude": destination["latitude"], "longitude": destination["longitude"]},
    ]
    assert len(route_points_in_high_risk) == 0, (
        "A* route wrongly passed through high-risk corridor.\n"
        f"direct_distance_km={direct_distance}\n"
        f"astar_distance_km={route['distance_km']}\n"
        f"route_points={route_points}\n"
        f"risk_values={[(point['latitude'], point['longitude'], point['risk_score'], point['risk_level']) for point in route_points]}\n"
        f"high_risk_points={route_points_in_high_risk}"
    )
    assert route["distance_km"] != direct_distance, (
        "A* route should differ from the direct line when avoiding a high-risk band.\n"
        f"direct_distance_km={direct_distance}\n"
        f"astar_distance_km={route['distance_km']}\n"
        f"route_points={route_points}\n"
        f"risk_values={[(point['latitude'], point['longitude'], point['risk_score'], point['risk_level']) for point in route_points]}"
    )
    assert route["distance_km"] > direct_distance * 0.95, (
        "A* route should be a real detour around the risk region rather than the direct path.\n"
        f"direct_distance_km={direct_distance}\n"
        f"astar_distance_km={route['distance_km']}\n"
        f"route_points={route_points}\n"
        f"risk_values={[(point['latitude'], point['longitude'], point['risk_score'], point['risk_level']) for point in route_points]}"
    )
    assert route["risk_score"] < 96.0, (
        "A* should reduce accumulated risk by avoiding the high-risk path.\n"
        f"direct_distance_km={direct_distance}\n"
        f"astar_distance_km={route['distance_km']}\n"
        f"route_points={route_points}\n"
        f"risk_values={[(point['latitude'], point['longitude'], point['risk_score'], point['risk_level']) for point in route_points]}"
    )

    # This is a behavior-first proof: the risk-aware route detours around the hazard
    # instead of sampling the direct line through a known synthetic risk corridor.
    assert route["distance_km"] > direct_distance


def test_route_optimizer_modes_still_return_valid_routes() -> None:
    for mode in ("SAFE", "BALANCED", "FUEL_SAVER"):
        route = RouteOptimizer.optimize_route(
            start={"latitude": -64.2, "longitude": 39.5},
            destination={"latitude": -65.0, "longitude": 41.0},
            departure_time_utc="2026-09-12T08:00:00Z",
            vessel={"speed_knots": 12},
            mode=mode,
        )
        assert route["mode"] == mode
        assert route["distance_km"] > 0
        assert len(route["route"]) >= 2
        assert route["cost_score"] >= 0
