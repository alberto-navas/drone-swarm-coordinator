import math

from src.geo import bearing_deg, centroid, haversine_distance_m, offset_point
from src.model import GeoPoint


def test_same_point_is_zero_distance() -> None:
    p = GeoPoint(lat=57.0, lon=10.0)
    assert haversine_distance_m(p, p) == 0.0


def test_one_degree_latitude_is_about_111_km() -> None:
    # A un grado de latitud le corresponden ~111.32 km en cualquier punto del
    # globo (el radio de la Tierra no varia con la latitud en un modelo
    # esferico); es la referencia mas simple para comprobar la formula.
    distance = haversine_distance_m(GeoPoint(0.0, 0.0), GeoPoint(1.0, 0.0))
    assert 111_000 < distance < 111_700


def test_offset_point_round_trips_with_haversine() -> None:
    origin = GeoPoint(lat=40.0, lon=-3.0)
    moved = offset_point(origin, north_m=100.0, east_m=50.0)
    distance = haversine_distance_m(origin, moved)
    assert math.isclose(distance, math.hypot(100.0, 50.0), rel_tol=0.01)


def test_offset_point_north_increases_latitude_only() -> None:
    origin = GeoPoint(lat=40.0, lon=-3.0)
    moved = offset_point(origin, north_m=200.0, east_m=0.0)
    assert moved.lat > origin.lat
    assert math.isclose(moved.lon, origin.lon, abs_tol=1e-9)


def test_bearing_north_is_zero() -> None:
    origin = GeoPoint(lat=40.0, lon=-3.0)
    north = offset_point(origin, north_m=500.0, east_m=0.0)
    assert math.isclose(bearing_deg(origin, north), 0.0, abs_tol=0.5)


def test_bearing_east_is_90() -> None:
    origin = GeoPoint(lat=40.0, lon=-3.0)
    east = offset_point(origin, north_m=0.0, east_m=500.0)
    assert math.isclose(bearing_deg(origin, east), 90.0, abs_tol=0.5)


def test_centroid_of_square() -> None:
    points = [GeoPoint(0.0, 0.0), GeoPoint(0.0, 2.0), GeoPoint(2.0, 0.0), GeoPoint(2.0, 2.0)]
    c = centroid(points)
    assert math.isclose(c.lat, 1.0)
    assert math.isclose(c.lon, 1.0)
