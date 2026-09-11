from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, field_validator


class NavigationMode(str, Enum):
    SAFE = "SAFE"
    BALANCED = "BALANCED"
    FUEL_SAVER = "FUEL_SAVER"


class Coordinate(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)


class Vessel(BaseModel):
    type: str = Field(..., min_length=1)
    speed_knots: float = Field(..., gt=0)
    fuel_rate: float = Field(..., ge=0)


class NavigationRequest(BaseModel):
    start: Coordinate
    destination: Coordinate
    departure_time_utc: str
    vessel: Vessel
    navigation_mode: NavigationMode

    @field_validator("departure_time_utc")
    @classmethod
    def validate_utc_timestamp(cls, value: str) -> str:
        if value.endswith("Z"):
            try:
                from datetime import datetime

                datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
                return value
            except ValueError as exc:
                raise ValueError("departure_time_utc must be a valid UTC ISO 8601 timestamp") from exc
        raise ValueError("departure_time_utc must be in UTC format ending with Z")
