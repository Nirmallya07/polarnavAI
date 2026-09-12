from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    FLASK_ENV: str = os.getenv("FLASK_ENV", "development")
    HOST: str = os.getenv("BACKEND_HOST", "127.0.0.1")
    PORT: int = int(os.getenv("BACKEND_PORT", "5000"))
    FRONTEND_PORT: int = int(os.getenv("FRONTEND_PORT", "5173"))
    COPERNICUS_DIR: str = os.getenv("POLARNAV_COPERNICUS_DIR", "/mnt/polarnav-drive")


config = Config()
