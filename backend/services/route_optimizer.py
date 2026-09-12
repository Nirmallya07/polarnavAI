"""A* route optimizer for the PolarNav decision-support layer.

This implementation keeps the route optimizer independent from model code and
uses a temporary local geographic grid plus time-aware risk lookups. The cost
function is intentionally development/MVP friendly: distance remains the base
cost, while risk, time, and fuel are non-negative penalties that shape route
selection without making the heuristic invalid.
"""

from __future__ import annotations

import heapq
from datetime import datetime, timedelta, timezone
from math import inf, sqrt

from backend.services.data_service import DataService
from backend.services.risk_engine import RiskEngine
from backend.utils.geo import haversine_km


class RouteOptimizer:
    """Compute a time-aware, risk-aware route using dynamic grid A* search."""

    MODE_WEIGHTS = {
        "SAFE": {"risk_weight": 2.2, "distance_weight": 0.8, "time_weight": 0.6, "fuel_weight": 0.2},
        "BALANCED": {"risk_weight": 1.5, "distance_weight": 1.0, "time_weight": 0.9, "fuel_weight": 0.4},
        "FUEL_SAVER": {"risk_weight": 1.0, "distance_weight": 1.3, "time_weight": 1.2, "fuel_weight": 0.9},
    }

    GRID_RESOLUTION_DEG = 0.25
    GRID_MARGIN_DEG = 1.5

    @staticmethod
    def _ensure_utc(value: str) -> datetime:
        if value.endswith("Z"):
            return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        raise ValueError("departure_time_utc must be in UTC format ending with Z")

    @staticmethod
    def _round_node(latitude: float, longitude: float) -> tuple[float, float]:
        return round(float(latitude), 6), round(float(longitude), 6)

    @staticmethod
    def _grid_bounds(start: dict, destination: dict) -> tuple[float, float, float, float]:
        lat_values = [float(start["latitude"]), float(destination["latitude"])]
        lon_values = [float(start["longitude"]), float(destination["longitude"])]
        min_lat = min(lat_values) - RouteOptimizer.GRID_MARGIN_DEG
        max_lat = max(lat_values) + RouteOptimizer.GRID_MARGIN_DEG
        min_lon = min(lon_values) - RouteOptimizer.GRID_MARGIN_DEG
        max_lon = max(lon_values) + RouteOptimizer.GRID_MARGIN_DEG
        return min_lat, max_lat, min_lon, max_lon

    @staticmethod
    def _build_grid(start: dict, destination: dict) -> set[tuple[float, float]]:
        min_lat, max_lat, min_lon, max_lon = RouteOptimizer._grid_bounds(start, destination)
        lat_step = RouteOptimizer.GRID_RESOLUTION_DEG
        lon_step = RouteOptimizer.GRID_RESOLUTION_DEG
        grid: set[tuple[float, float]] = set()
        current_lat = min_lat
        while current_lat <= max_lat + 1e-9:
            current_lon = min_lon
            while current_lon <= max_lon + 1e-9:
                grid.add(RouteOptimizer._round_node(current_lat, current_lon))
                current_lon += lon_step
            current_lat += lat_step
        grid.add(RouteOptimizer._round_node(start["latitude"], start["longitude"]))
        grid.add(RouteOptimizer._round_node(destination["latitude"], destination["longitude"]))
        return grid

    @staticmethod
    def _neighbors(node: tuple[float, float], grid: set[tuple[float, float]], resolution_deg: float) -> list[tuple[float, float]]:
        latitude, longitude = node
        neighbor_nodes: list[tuple[float, float]] = []
        deltas = [
            (-1, -1), (-1, 0), (-1, 1),
            (0, -1),           (0, 1),
            (1, -1),  (1, 0),  (1, 1),
        ]
        for delta_lat, delta_lon in deltas:
            candidate = (
                round(latitude + delta_lat * resolution_deg, 6),
                round(longitude + delta_lon * resolution_deg, 6),
            )
            if candidate in grid:
                neighbor_nodes.append(candidate)
        return neighbor_nodes

    @staticmethod
    def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        return haversine_km(lat1, lon1, lat2, lon2)

    @staticmethod
    def _estimate_travel_time_hours(speed_knots: float, distance_km: float) -> float:
        if speed_knots <= 0:
            return 0.0
        return distance_km / (speed_knots * 1.852)

    @staticmethod
    def _heuristic_cost(current: tuple[float, float], destination: tuple[float, float], distance_weight: float) -> float:
        """Return an admissible lower bound using the base distance term only.

        The route cost includes additional non-negative risk/time/fuel penalties,
        but the heuristic must remain a lower bound. Therefore it uses only the
        minimum guaranteed movement-distance contribution.
        """
        current_lat, current_lon = current
        goal_lat, goal_lon = destination
        raw_distance = RouteOptimizer._distance_km(current_lat, current_lon, goal_lat, goal_lon)
        return raw_distance * distance_weight

    @staticmethod
    def _movement_cost(
        distance_km: float,
        risk_score: float,
        travel_time_hours: float,
        fuel_proxy: float,
        weights: dict,
    ) -> float:
        """Development/MVP cost function.

        Distance is the base cost. Risk, time, and fuel are additional non-negative
        penalties. The weights are provisional and should be revalidated once
        operational vessel/fuel models are available.
        """
        distance_component = distance_km * weights["distance_weight"]
        # Risk is intentionally a strong but bounded penalty for MVP routing.
        # The direct line through a high-risk band should be substantially more
        # expensive than a longer low-risk detour.
        risk_component = (risk_score / 100.0) * distance_km * weights["risk_weight"] * 12.0
        time_component = travel_time_hours * 12.0 * weights["time_weight"]
        fuel_component = fuel_proxy * weights["fuel_weight"] * 0.05
        return distance_component + risk_component + time_component + fuel_component

    @staticmethod
    def _reconstruct_path(
        came_from: dict,
        current: tuple[float, float],
        start: tuple[float, float],
    ) -> list[tuple[float, float]]:
        path = [current]
        while current in came_from and current != start:
            current = came_from[current]
            path.append(current)
        path.reverse()
        return path

    @staticmethod
    def _normalize_point(point: dict) -> dict:
        return {
            "latitude": float(point["latitude"]),
            "longitude": float(point["longitude"]),
        }

    @staticmethod
    def optimize_route(
        start: dict | None = None,
        destination: dict | None = None,
        departure_time_utc: str | None = None,
        vessel: dict | None = None,
        mode: str = "BALANCED",
        environment_lookup=None,
        risk_evaluator=None,
    ) -> dict:
        start_point = RouteOptimizer._normalize_point(start or {"latitude": -64.2, "longitude": 39.5})
        destination_point = RouteOptimizer._normalize_point(destination or {"latitude": -65.0, "longitude": 41.0})
        departure = departure_time_utc or "2026-09-12T08:00:00Z"
        vessel_info = vessel or {"speed_knots": 12.0}
        mode_value = str(mode or "BALANCED").upper()
        if mode_value not in RouteOptimizer.MODE_WEIGHTS:
            mode_value = "BALANCED"

        if environment_lookup is None:
            environment_lookup = DataService.get_environment
        if risk_evaluator is None:
            risk_evaluator = RiskEngine.evaluate_risk

        weights = RouteOptimizer.MODE_WEIGHTS[mode_value]
        start_key = RouteOptimizer._round_node(start_point["latitude"], start_point["longitude"])
        goal_key = RouteOptimizer._round_node(destination_point["latitude"], destination_point["longitude"])
        grid = RouteOptimizer._build_grid(start_point, destination_point)
        if start_key not in grid:
            grid.add(start_key)
        if goal_key not in grid:
            grid.add(goal_key)

        open_heap: list[tuple[float, int, tuple[float, float]]] = []
        heapq.heappush(open_heap, (0.0, 0, start_key))
        came_from: dict[tuple[float, float], tuple[float, float]] = {}
        g_score: dict[tuple[float, float], float] = {start_key: 0.0}
        f_score: dict[tuple[float, float], float] = {start_key: RouteOptimizer._heuristic_cost(start_key, goal_key, weights["distance_weight"])}
        closed: set[tuple[float, float]] = set()
        arrival_times: dict[tuple[float, float], datetime] = {start_key: RouteOptimizer._ensure_utc(departure)}
        edge_costs: dict[tuple[tuple[float, float], tuple[float, float]], float] = {}

        while open_heap:
            _, _, current = heapq.heappop(open_heap)
            if current in closed:
                continue
            if current == goal_key:
                break
            closed.add(current)

            for neighbor in RouteOptimizer._neighbors(current, grid, RouteOptimizer.GRID_RESOLUTION_DEG):
                if neighbor in closed:
                    continue
                distance_km = RouteOptimizer._distance_km(
                    current[0], current[1], neighbor[0], neighbor[1]
                )
                travel_hours = RouteOptimizer._estimate_travel_time_hours(
                    float(vessel_info.get("speed_knots", 12.0)),
                    distance_km,
                )
                arrival_time = arrival_times[current] + timedelta(hours=travel_hours)
                environment_state = environment_lookup(
                    neighbor[0],
                    neighbor[1],
                    arrival_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                )
                risk_result = risk_evaluator(environment_state)
                risk_score = float(risk_result.get("risk_score", 0.0))
                fuel_proxy = max(0.0, distance_km * 0.8 + risk_score * 0.6)
                movement_cost = RouteOptimizer._movement_cost(
                    distance_km,
                    risk_score,
                    travel_hours,
                    fuel_proxy,
                    weights,
                )
                edge_costs[(current, neighbor)] = movement_cost
                tentative_g = g_score.get(current, inf) + movement_cost
                if tentative_g < g_score.get(neighbor, inf):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    arrival_times[neighbor] = arrival_time
                    f_score[neighbor] = tentative_g + RouteOptimizer._heuristic_cost(neighbor, goal_key, weights["distance_weight"])
                    heapq.heappush(open_heap, (f_score[neighbor], len(open_heap), neighbor))

        if goal_key not in g_score:
            final_path = [start_key, goal_key]
            route_points = []
            for node in final_path:
                route_points.append({
                    "latitude": round(node[0], 4),
                    "longitude": round(node[1], 4),
                    "arrival_time_utc": departure,
                    "risk_score": 0.0,
                    "risk_level": "LOW",
                })
            return {
                "mode": mode_value,
                "route": route_points,
                "risk_score": 0.0,
                "distance_km": round(RouteOptimizer._distance_km(start_point["latitude"], start_point["longitude"], destination_point["latitude"], destination_point["longitude"]), 2),
                "eta_hours": 0.0,
                "fuel_estimate": 0.0,
                "cost_score": 0.0,
            }

        route_nodes = RouteOptimizer._reconstruct_path(came_from, goal_key, start_key)
        route = []
        total_distance = 0.0
        edge_cost_total = 0.0
        step_risks = []
        last_node = None

        for node in route_nodes:
            arrival_time = arrival_times.get(node, RouteOptimizer._ensure_utc(departure))
            environment_state = environment_lookup(
                node[0],
                node[1],
                arrival_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            )
            risk_result = risk_evaluator(environment_state)
            route.append(
                {
                    "latitude": round(node[0], 4),
                    "longitude": round(node[1], 4),
                    "arrival_time_utc": arrival_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "risk_score": round(float(risk_result.get("risk_score", 0.0)), 2),
                    "risk_level": risk_result.get("risk_level", "LOW"),
                    "eta_hours": round((arrival_time - RouteOptimizer._ensure_utc(departure)).total_seconds() / 3600.0, 2),
                }
            )
            step_risks.append(float(risk_result.get("risk_score", 0.0)))
            if last_node is not None:
                total_distance += RouteOptimizer._distance_km(last_node[0], last_node[1], node[0], node[1])
                edge_cost_total += edge_costs.get((last_node, node), 0.0)
            last_node = node

        risk_score = round(sum(step_risks) / max(len(step_risks), 1), 2)
        eta_hours = round((route[-1]["eta_hours"] if route else 0.0), 2)
        fuel_proxy = max(0.0, total_distance * 0.8 + risk_score * 0.6)
        total_cost = edge_cost_total if edge_cost_total > 0 else max(0.0, total_distance * weights["distance_weight"] + risk_score * weights["risk_weight"])

        return {
            "mode": mode_value,
            "route": route,
            "risk_score": risk_score,
            "distance_km": round(total_distance, 2),
            "eta_hours": eta_hours,
            "fuel_estimate": round(fuel_proxy, 2),
            "cost_score": round(total_cost, 2),
        }
