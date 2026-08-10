from src.allocation import assign_point_tasks, greedy_nearest_pairing, plan_area_coverage
from src.geo import haversine_distance_m
from src.model import Drone, GeoPoint, Task, TaskType


def _drone(id_: str, lat: float, lon: float) -> Drone:
    return Drone(id=id_, position=GeoPoint(lat=lat, lon=lon))


def _point_task(id_: str, lat: float, lon: float, priority: int = 1) -> Task:
    return Task(id=id_, type=TaskType.DESTINATION, points=[GeoPoint(lat=lat, lon=lon)], priority=priority)


def test_greedy_nearest_pairing_picks_closest_pair_first() -> None:
    agents = [("a1", GeoPoint(0.0, 0.0)), ("a2", GeoPoint(10.0, 10.0))]
    targets = [("t1", GeoPoint(0.001, 0.001)), ("t2", GeoPoint(10.001, 10.001))]
    pairing = greedy_nearest_pairing(agents, targets)
    assert pairing == {"a1": "t1", "a2": "t2"}


def test_greedy_nearest_pairing_leaves_surplus_unassigned() -> None:
    agents = [("a1", GeoPoint(0.0, 0.0))]
    targets = [("t1", GeoPoint(0.0, 0.001)), ("t2", GeoPoint(0.0, 0.002))]
    pairing = greedy_nearest_pairing(agents, targets)
    assert len(pairing) == 1
    assert pairing["a1"] == "t1"


def test_assign_point_tasks_matches_each_drone_to_nearest_free_task() -> None:
    drones = [_drone("d1", 0.0, 0.0), _drone("d2", 5.0, 5.0)]
    tasks = [_point_task("t1", 0.001, 0.001), _point_task("t2", 5.001, 5.001)]
    pairing = assign_point_tasks(drones, tasks)
    assert pairing == {"d1": "t1", "d2": "t2"}


def test_assign_point_tasks_serves_higher_priority_first_when_drones_scarce() -> None:
    # Un unico dron, dos tareas: la de prioridad mas baja esta mas cerca,
    # pero la de prioridad mas alta debe servirse igualmente antes.
    drones = [_drone("d1", 0.0, 0.0)]
    low_priority_near = _point_task("low", 0.001, 0.001, priority=1)
    high_priority_far = _point_task("high", 1.0, 1.0, priority=5)
    pairing = assign_point_tasks(drones, [low_priority_near, high_priority_far])
    assert pairing == {"d1": "high"}


def test_plan_area_coverage_assigns_one_cell_per_drone() -> None:
    drones = [_drone(f"d{i}", 0.0, 0.0) for i in range(4)]
    task = Task(id="area1", type=TaskType.AREA, points=[GeoPoint(0.0, 0.0), GeoPoint(1.0, 1.0)])
    routes = plan_area_coverage(drones, task)
    assert set(routes) == {d.id for d in drones}


def test_plan_area_coverage_routes_stay_within_cell_bounds() -> None:
    drones = [_drone(f"d{i}", 0.0, 0.0) for i in range(2)]
    task = Task(id="area1", type=TaskType.AREA, points=[GeoPoint(0.0, 0.0), GeoPoint(2.0, 1.0)])
    routes = plan_area_coverage(drones, task)
    for route in routes.values():
        for point in route:
            assert 0.0 <= point.lat <= 2.0
            assert 0.0 <= point.lon <= 1.0


def test_plan_area_coverage_empty_without_drones() -> None:
    task = Task(id="area1", type=TaskType.AREA, points=[GeoPoint(0.0, 0.0), GeoPoint(1.0, 1.0)])
    assert plan_area_coverage([], task) == {}


def test_plan_area_coverage_cells_are_closer_to_assigned_drone_than_alternative() -> None:
    # No es optimo globalmente (ver docstring del modulo), pero cada dron
    # debe quedar razonablemente cerca de su celda: comprobamos que la
    # celda asignada no este absurdamente mas lejos que el centro del area.
    drones = [_drone("near", 0.0, 0.0), _drone("far", 5.0, 5.0)]
    task = Task(id="area1", type=TaskType.AREA, points=[GeoPoint(0.0, 0.0), GeoPoint(1.0, 1.0)])
    routes = plan_area_coverage(drones, task)
    near_first_point = routes["near"][0]
    assert haversine_distance_m(GeoPoint(0.0, 0.0), near_first_point) < haversine_distance_m(
        GeoPoint(5.0, 5.0), near_first_point
    )
