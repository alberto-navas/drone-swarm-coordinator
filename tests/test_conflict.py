import math

from src.conflict import detect_conflicts, separation_offset_m
from src.geo import offset_point
from src.model import Drone, GeoPoint


def _drone(id_: str, position: GeoPoint) -> Drone:
    return Drone(id=id_, position=position)


def test_detect_conflicts_flags_pair_closer_than_threshold() -> None:
    origin = GeoPoint(lat=40.0, lon=-3.0)
    close = offset_point(origin, north_m=5.0, east_m=0.0)
    drones = [_drone("a", origin), _drone("b", close)]
    events = detect_conflicts(drones, min_separation_m=15.0, tick=3)
    assert len(events) == 1
    assert {events[0].drone_a_id, events[0].drone_b_id} == {"a", "b"}
    assert events[0].tick == 3


def test_detect_conflicts_ignores_pair_beyond_threshold() -> None:
    origin = GeoPoint(lat=40.0, lon=-3.0)
    far = offset_point(origin, north_m=500.0, east_m=0.0)
    drones = [_drone("a", origin), _drone("b", far)]
    assert detect_conflicts(drones, min_separation_m=15.0, tick=0) == []


def test_detect_conflicts_scales_with_number_of_close_pairs() -> None:
    origin = GeoPoint(lat=40.0, lon=-3.0)
    drones = [_drone(f"d{i}", origin) for i in range(3)]  # los 3 coincidentes
    events = detect_conflicts(drones, min_separation_m=15.0, tick=0)
    assert len(events) == 3  # C(3, 2)


def test_separation_offset_is_zero_when_no_one_is_close() -> None:
    origin = GeoPoint(lat=40.0, lon=-3.0)
    far = offset_point(origin, north_m=500.0, east_m=0.0)
    drone = _drone("a", origin)
    other = _drone("b", far)
    assert separation_offset_m(drone, [drone, other], min_separation_m=15.0) == (0.0, 0.0)


def test_separation_offset_pushes_away_from_intruder() -> None:
    origin = GeoPoint(lat=40.0, lon=-3.0)
    # Intruso justo al norte, dentro del radio minimo: el vector de escape
    # debe apuntar hacia el sur (componente norte negativa).
    intruder_position = offset_point(origin, north_m=5.0, east_m=0.0)
    drone = _drone("a", origin)
    intruder = _drone("b", intruder_position)
    north, east = separation_offset_m(drone, [drone, intruder], min_separation_m=15.0)
    assert north < 0.0
    assert math.isclose(east, 0.0, abs_tol=1e-9)


def test_separation_offset_ignores_self() -> None:
    origin = GeoPoint(lat=40.0, lon=-3.0)
    drone = _drone("a", origin)
    assert separation_offset_m(drone, [drone], min_separation_m=15.0) == (0.0, 0.0)
