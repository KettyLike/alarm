from distance import haversine_distance_km


def test_same_point_is_zero() -> None:
    assert haversine_distance_km(50.0, 30.0, 50.0, 30.0) == 0


def test_kyiv_to_fastiv_is_about_55_km() -> None:
    distance = haversine_distance_km(50.4501, 30.5234, 50.0767, 29.9177)
    assert 50 < distance < 60