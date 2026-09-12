"""Risk scoring for environmental and prediction-derived hazards.

This implementation intentionally uses configurable, provisional weights and a
clear time-aware interface so the downstream route optimizer can operate before
real model artifacts are available.
"""

from __future__ import annotations

from math import sqrt


class RiskEngine:
    """Compute time-aware risk scores from environmental and model signals."""

    DEFAULT_WEIGHTS = {
        "sea_ice": 0.35,
        "iceberg": 0.30,
        "weather": 0.20,
        "ocean": 0.15,
    }

    RISK_LEVELS = (
        (25, "LOW"),
        (50, "MODERATE"),
        (75, "HIGH"),
        (101, "CRITICAL"),
    )

    @staticmethod
    def _clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
        return max(minimum, min(maximum, value))

    @staticmethod
    def _risk_level_for(score: float) -> str:
        for threshold, label in RiskEngine.RISK_LEVELS:
            if score <= threshold:
                return label
        return "CRITICAL"

    @staticmethod
    def evaluate_risk(environment_state: dict | None = None) -> dict:
        state = environment_state or {}
        sea_ice = float(state.get("sea_ice_concentration", 0.0) or 0.0)
        iceberg = float(state.get("iceberg_risk", state.get("iceberg_score", 0.0)) or 0.0)
        wind_speed = float(state.get("wind_speed_kts", 0.0) or 0.0)
        wind_u = float(state.get("wind_u10", 0.0) or 0.0)
        wind_v = float(state.get("wind_v10", 0.0) or 0.0)
        wave_height = float(state.get("wave_height", 0.0) or 0.0)
        ocean_u = float(state.get("ocean_u", 0.0) or 0.0)
        ocean_v = float(state.get("ocean_v", 0.0) or 0.0)

        wind_mag = sqrt(float(wind_u) ** 2 + float(wind_v) ** 2)
        if wind_speed == 0.0 and wind_mag:
            wind_speed = wind_mag

        current_mag = sqrt(float(ocean_u) ** 2 + float(ocean_v) ** 2)

        sea_ice_component = RiskEngine._clamp(sea_ice * 100.0)
        iceberg_component = RiskEngine._clamp(iceberg)
        weather_component = RiskEngine._clamp(
            (wind_speed / 25.0) * 40.0 + (wave_height / 6.0) * 60.0
        )
        ocean_component = RiskEngine._clamp((current_mag / 2.5) * 100.0)

        risk_score = (
            RiskEngine.DEFAULT_WEIGHTS["sea_ice"] * sea_ice_component
            + RiskEngine.DEFAULT_WEIGHTS["iceberg"] * iceberg_component
            + RiskEngine.DEFAULT_WEIGHTS["weather"] * weather_component
            + RiskEngine.DEFAULT_WEIGHTS["ocean"] * ocean_component
        )
        risk_score = RiskEngine._clamp(risk_score)

        return {
            "timestamp_utc": state.get("timestamp_utc"),
            "latitude": state.get("latitude"),
            "longitude": state.get("longitude"),
            "risk_score": round(risk_score, 2),
            "risk_level": RiskEngine._risk_level_for(risk_score),
            "components": {
                "sea_ice": round(sea_ice_component, 2),
                "iceberg": round(iceberg_component, 2),
                "weather": round(weather_component, 2),
                "ocean": round(ocean_component, 2),
            },
        }
