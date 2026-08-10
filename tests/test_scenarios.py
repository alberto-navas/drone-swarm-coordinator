from src.model import TaskType
from src.scenarios import DRONE_COUNT, area_coverage_conflict_scenario, formation_transit_scenario
from src.simulation import run


def test_area_coverage_scenario_has_expected_drone_count_and_single_area_task() -> None:
    drones, mission = area_coverage_conflict_scenario()
    assert len(drones) == DRONE_COUNT
    assert [t.type for t in mission.tasks] == [TaskType.AREA]
    assert mission.formation is None


def test_area_coverage_scenario_drones_all_start_at_the_same_launch_point() -> None:
    drones, _ = area_coverage_conflict_scenario()
    positions = {(d.position.lat, d.position.lon) for d in drones}
    assert len(positions) == 1


def test_area_coverage_scenario_produces_early_conflicts_and_resolves_by_the_end() -> None:
    # Todos arrancan en el mismo punto (separacion 0m): los primeros ticks
    # deben generar conflictos que la evitacion resuelve mientras cada dron
    # se dirige a su celda.
    drones, mission = area_coverage_conflict_scenario(drone_count=6)
    history = run(drones, mission, n_ticks=90)
    assert len(history[1].conflicts) > 0
    assert history[-1].tick == 90


def test_formation_transit_scenario_has_no_tasks_and_a_v_formation() -> None:
    drones, mission = formation_transit_scenario()
    assert len(drones) == DRONE_COUNT
    assert mission.tasks == []
    assert mission.formation is not None
    assert mission.formation.shape.value == "v"


def test_formation_transit_scenario_drones_start_already_spread_out() -> None:
    drones, _ = formation_transit_scenario()
    positions = {(round(d.position.lat, 6), round(d.position.lon, 6)) for d in drones}
    assert len(positions) == len(drones)
