from __future__ import annotations

from pydantic import BaseModel, Field


class EnvironmentInput(BaseModel):
    timestamp_utc: str
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    sea_ice_concentration: float | None = Field(default=None, ge=0.0, le=1.0)
    wind_u10: float | None = None
    wind_v10: float | None = None
    air_temperature: float | None = None
    ocean_u: float | None = None
    ocean_v: float | None = None
    wave_height: float | None = None
    wave_period: float | None = None
