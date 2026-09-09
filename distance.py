from __future__ import annotations

from math import asin, cos, radians, sin, sqrt


EARTH_RADIUS_KM = 6371.0088


def haversine_distance_km(
    first_lat: float,
    first_lon: float,
    second_lat: float,
    second_lon: float,
) -> float:
    latitude_delta = radians(second_lat - first_lat)
    longitude_delta = radians(second_lon - first_lon)
    first_latitude = radians(first_lat)
    second_latitude = radians(second_lat)

    haversine_value = (
        sin(latitude_delta / 2) ** 2
        + cos(first_latitude)
        * cos(second_latitude)
        * sin(longitude_delta / 2) ** 2
    )
    haversine_value = min(1.0, max(0.0, haversine_value))
    return EARTH_RADIUS_KM * 2 * asin(sqrt(haversine_value))