import math

from src.formation import _local_offsets, _mean_heading_deg, formation_targets
from src.geo import haversine_distance_m
from src.model import Drone, FormationConfig, FormationShape, GeoPoint


def _drone(id_: str, lat: float = 0.0, lon: float = 0.0, heading_deg: float = 0.0) -> Drone:
    return Drone(id=id_, position=GeoPoint(lat=lat, lon=lon), heading_deg=heading_deg)


def test_mean_heading_deg_wraps_around_north() -> None:
    # 350 y 10 grados estan a 20 grados de distancia cruzando el norte;
    # la media aritmetica ingenua (180) seria justo la opuesta.
    assert math.isclose(_mean_heading_deg([350.0, 10.0]), 0.0, abs_tol=1e-6)


def test_line_offsets_are_symmetric_around_center() -> None:
    offsets = _local_offsets(FormationShape.LINE, n=3, spacing_m=10.0)
    sides = sorted(side for _, side in offsets)
    assert sides == [-10.0, 0.0, 10.0]
    assert all(forward == 0.0 for forward, _ in offsets)


def test_v_offsets_start_at_origin_and_alternate_arms() -> None:
    offsets = _local_offsets(FormationShape.V, n=5, spacing_m=10.0)
    assert offsets[0] == (0.0, 0.0)
    # Los siguientes dos deben estar al mismo "adelante" (mismo brazo de la
    # cuna), en lados opuestos.
    assert offsets[1][0] == offsets[2][0]
    assert offsets[1][1] == -offsets[2][1]


def test_grid_offsets_produce_expected_row_count() -> None:
    offsets = _local_offsets(FormationShape.GRID, n=4, spacing_m=10.0)
    rows = {round(forward / -10.0) for forward, _ in offsets}
    assert rows == {0, 1}


def test_formation_targets_line_centered_on_centroid() -> None:
    drones = [_drone("d0", lat=0.0, lon=0.0), _drone("d1", lat=0.0, lon=0.0)]
    config = FormationConfig(shape=FormationShape.LINE, spacing_m=20.0)
    targets = formation_targets(drones, config)
    assert set(targets) == {"d0", "d1"}
    dist_between_slots = haversine_distance_m(targets["d0"], targets["d1"])
    assert math.isclose(dist_between_slots, 20.0, rel_tol=0.05)


def test_formation_targets_assigns_nearest_slot_not_arbitrary_order() -> None:
    # d_right ya esta al lado derecho del centroide: debe quedarse con el
    # hueco derecho, no el izquierdo, aunque en la lista de drones vaya
    # primero d_left.
    d_left = _drone("d_left", lat=0.0, lon=-0.001)
    d_right = _drone("d_right", lat=0.0, lon=0.001)
    config = FormationConfig(shape=FormationShape.LINE, spacing_m=30.0)
    targets = formation_targets([d_left, d_right], config)
    assert targets["d_right"].lon > targets["d_left"].lon


def test_formation_targets_uses_leader_position_when_set() -> None:
    leader = _drone("leader", lat=10.0, lon=10.0)
    follower = _drone("follower", lat=0.0, lon=0.0)
    config = FormationConfig(shape=FormationShape.LINE, spacing_m=20.0, leader_id="leader")
    targets = formation_targets([leader, follower], config)
    # Con lider fijado, los huecos se centran en la posicion del lider, muy
    # lejos de (0,0), no en el centroide (que estaria a mitad de camino.
    assert haversine_distance_m(GeoPoint(10.0, 10.0), targets["leader"]) < 50.0


def test_formation_targets_empty_without_drones() -> None:
    config = FormationConfig(shape=FormationShape.GRID)
    assert formation_targets([], config) == {}
