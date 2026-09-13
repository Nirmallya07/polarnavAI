from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.append("/mnt/polarnav-models")

from sea_ice_project_module.inference import predict_sea_ice

from backend.services.environment_history_coordinator import EnvironmentalHistoryCoordinator
from backend.services.patch_assembler import SeaIcePatchAssembler


def test_real_patch_assembler_builds_model_input_and_predicts() -> None:
    coordinator = EnvironmentalHistoryCoordinator()
    history = coordinator.get_environment_history(
        latitude=-64.0,
        longitude=12.0,
        requested_time_utc="2023-09-15T00:00:00Z",
    )

    assert history["status"] == "history_complete"
    assert len(history["timestamps"]) == 15

    assembler = SeaIcePatchAssembler()
    tensor = assembler.build_model_input(
        center_latitude=-64.0,
        center_longitude=12.0,
        history_timestamps=history["timestamps"],
    )

    assert tensor.shape == (15, 15, 15, 9)
    assert np.isfinite(tensor).all()

    forecast = predict_sea_ice(tensor)
    assert forecast.shape == (5, 15, 15)
    assert np.isfinite(forecast).all()
    assert forecast.min() >= 0.0
    assert forecast.max() <= 1.0
