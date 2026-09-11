from __future__ import annotations

from pydantic import BaseModel, Field


class EnvironmentInput(BaseModel):
    timestamp_utc: str
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    sea_surface_temp_c: float | None = None
    wind_speed_kts: float | None = None
    wave_height_m: float | None = None
    ice_concentration_pct: float | None = None
