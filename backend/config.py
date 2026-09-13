from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    FLASK_ENV: str = os.getenv("FLASK_ENV", "development")
    HOST: str = os.getenv("BACKEND_HOST", "127.0.0.1")
    PORT: int = int(os.getenv("BACKEND_PORT", "5000"))
    FRONTEND_PORT: int = int(os.getenv("FRONTEND_PORT", "5173"))
    COPERNICUS_DIR: str = os.getenv("POLARNAV_COPERNICUS_DIR", "/mnt/polarnav-models/2023_final")
    NSIDC_DIR: str = os.getenv("POLARNAV_NSIDC_DIR", "/mnt/polarnav-models")
    ERA5_DATA_DIR: str = os.getenv("ERA5_DATA_DIR", "/mnt/polarnav-models/PolarNav_Weather_Dataset_2023/daily")
    SEA_ICE_MODEL_DIR: str = os.getenv(
        "POLARNAV_SEA_ICE_MODEL_DIR",
        "/mnt/polarnav-models/sea_ice_project_module",
    )


config = Config()
