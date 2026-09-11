"""Time utilities for navigation and risk computations."""

from __future__ import annotations

from datetime import datetime, timezone


def ensure_utc_timestamp(value: str) -> datetime:
    """Parse a UTC ISO timestamp and return a timezone-aware datetime."""
    if value.endswith("Z"):
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
        return parsed.replace(tzinfo=timezone.utc)
    raise ValueError("Timestamp must end with Z to indicate UTC")
