from __future__ import annotations

from pydantic import BaseModel, Field


class PredictionPoint(BaseModel):
    timestamp_utc: str
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    probability: float | None = Field(default=None, ge=0.0, le=1.0)
