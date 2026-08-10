import math

from src.geo import haversine_distance_m, offset_point
from src.model import (
    Drone,
    DroneStatus,
    FormationConfig,
    FormationShape,
    GeoPoint,
    Mission,
    SimulationState,
    Task,
    TaskType,
)
from src.simulation import BATTERY_DRAIN_PCT_PER_S_IDLE, TICK_SECONDS, _advance_drone, build_initial_state, run, step


def test_build_initial_state_assigns_nearest_destination() -> None:
    drone = Drone(id="d1", position=GeoPoint(lat=40.0, lon=-3.0))
    target = GeoPoint(lat=40.001, lon=-3.0)
    task = Task(id="t1", type=TaskType.DESTINATION, points=[target])
    mission = Mission(id="m1", tasks=[task])
    state = build_initial_state([drone], mission)
    assert state.drones[0].assigned_task_id == "t1"
    assert state.drones[0].target == target
    assert state.drones[0].status == DroneStatus.EN_ROUTE


def test_build_initial_state_does_not_double_assign_a_drone() -> None:
    drone = Drone(id="d1", position=GeoPoint(lat=0.0, lon=0.0))
    point_task = Task(id="p1", type=TaskType.DESTINATION, points=[GeoPoint(lat=0.0001, lon=0.0)])
    area_task = Task(id="a1", type=TaskType.AREA, points=[GeoPoint(lat=1.0, lon=1.0), GeoPoint(lat=2.0, lon=2.0)])
    mission = Mission(id="m", tasks=[point_task, area_task])
    state = build_initial_state([drone], mission)
    assert state.drones[0].assigned_task_id == "p1"
    assert state.drones[0].route == []  # no quedo ningun dron libre para la tarea de area


def test_run_drone_arrives_on_station_at_destination() -> None:
    drone = Drone(id="d1", position=GeoPoint(lat=40.0, lon=-3.0), speed_mps=20.0)
    target = offset_point(drone.position, north_m=100.0, east_m=0.0)
    task = Task(id="t1", type=TaskType.DESTINATION, points=[target])
    mission = Mission(id="m1", tasks=[task])
    history = run([drone], mission, n_ticks=20)
    final = history[-1].drones[0]
    assert final.status == DroneStatus.ON_STATION
    assert haversine_distance_m(final.position, target) < 5.0


def test_run_area_task_consumes_full_sweep_route() -> None:
    drones = [Drone(id="d1", position=GeoPoint(lat=0.0, lon=0.0), speed_mps=50.0)]
    task = Task(id="area1", type=TaskType.AREA, points=[GeoPoint(lat=0.0, lon=0.0), GeoPoint(lat=0.001, lon=0.001)])
    mission = Mission(id="m", tasks=[task])
    history = run(drones, mission, n_ticks=200)
    final = history[-1].drones[0]
    assert final.route == []
    assert final.status == DroneStatus.ON_STATION


def test_run_formation_converges_to_target_spacing() -> None:
    drones = [
        Drone(id="d0", position=GeoPoint(lat=0.0, lon=0.0), speed_mps=10.0),
        Drone(id="d1", position=GeoPoint(lat=0.0, lon=0.0001), speed_mps=10.0),
    ]
    mission = Mission(id="m", tasks=[], formation=FormationConfig(shape=FormationShape.LINE, spacing_m=20.0))
    history = run(drones, mission, n_ticks=15)
    final_drones = history[-1].drones
    distance = haversine_distance_m(final_drones[0].position, final_drones[1].position)
    assert math.isclose(distance, 20.0, rel_tol=0.2)


def test_step_separation_pushes_apart_drones_flying_in_parallel() -> None:
    # Dos drones muy juntos, con el mismo destino lejano: sin correccion se
    # moverian en paralelo manteniendo la misma separacion insegura para
    # siempre. Con la correccion activa, la separacion debe crecer.
    origin = GeoPoint(lat=40.0, lon=-3.0)
    close = offset_point(origin, north_m=5.0, east_m=0.0)
    far_target = offset_point(origin, north_m=0.0, east_m=10_000.0)
    drone_a = Drone(id="a", position=origin, target=far_target, status=DroneStatus.EN_ROUTE)
    drone_b = Drone(id="b", position=close, target=far_target, status=DroneStatus.EN_ROUTE)
    state = SimulationState(tick=0, drones=[drone_a, drone_b])
    mission = Mission(id="m", tasks=[])

    before = haversine_distance_m(drone_a.position, drone_b.position)
    new_state = step(state, mission, min_separation_m=15.0)
    after = haversine_distance_m(new_state.drones[0].position, new_state.drones[1].position)

    assert after > before


def test_step_records_conflict_event_when_drones_are_too_close() -> None:
    origin = GeoPoint(lat=40.0, lon=-3.0)
    close = offset_point(origin, north_m=5.0, east_m=0.0)
    state = SimulationState(
        tick=0,
        drones=[Drone(id="a", position=origin), Drone(id="b", position=close)],
    )
    mission = Mission(id="m", tasks=[])
    new_state = step(state, mission, min_separation_m=15.0)
    assert len(new_state.conflicts) == 1
    assert new_state.conflicts[0].tick == 1


def test_advance_drone_idle_drains_battery_slowly() -> None:
    drone = Drone(id="a", position=GeoPoint(lat=0.0, lon=0.0), battery_pct=100.0)
    updated = _advance_drone(drone, target=None, all_drones=[drone], min_separation_m=15.0)
    assert math.isclose(updated.battery_pct, 100.0 - BATTERY_DRAIN_PCT_PER_S_IDLE * TICK_SECONDS)


def test_advance_drone_grounds_when_battery_reaches_zero() -> None:
    drone = Drone(id="a", position=GeoPoint(lat=0.0, lon=0.0), battery_pct=0.001, status=DroneStatus.IDLE)
    updated = _advance_drone(drone, target=None, all_drones=[drone], min_separation_m=15.0)
    assert updated.status == DroneStatus.GROUNDED
    assert updated.battery_pct == 0.0


def test_advance_drone_grounded_drone_never_moves() -> None:
    position = GeoPoint(lat=0.0, lon=0.0)
    drone = Drone(id="a", position=position, status=DroneStatus.GROUNDED, battery_pct=0.0)
    updated = _advance_drone(drone, target=GeoPoint(lat=1.0, lon=1.0), all_drones=[drone], min_separation_m=15.0)
    assert updated.position == position
