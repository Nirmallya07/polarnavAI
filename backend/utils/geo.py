"""Geospatial helper functions for PolarNav AI."""


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return approximate distance in kilometers between two coordinates."""
    from math import atan2, cos, radians, sin, sqrt

    radius_km = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    )
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return radius_km * c
