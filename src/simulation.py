"""
Bucle de simulacion del enjambre: avanza el estado en pasos discretos
(ticks), combinando reparto de mision (src/allocation.py), formacion
(src/formation.py) y deteccion/correccion de conflictos
(src/conflict.py) sobre una cinematica de vuelo minima (velocidad de
crucero constante hacia el punto objetivo, sin modelo de aceleracion ni
viento).

Esto es un simulador de planificacion y visualizacion: no hay control de
vuelo real ni conexion a hardware (ver seccion de limites del README).
"""

import math

from src.allocation import assign_point_tasks, plan_area_coverage
from src.conflict import detect_conflicts, separation_offset_m
from src.formation import formation_targets
from src.geo import bearing_deg, haversine_distance_m, offset_point
from src.model import Drone, DroneStatus, GeoPoint, Mission, SimulationState, TaskType

TICK_SECONDS = 1.0
DEFAULT_MIN_SEPARATION_M = 15.0
ARRIVAL_EPSILON_M = 2.0
BATTERY_DRAIN_PCT_PER_S_MOVING = 0.05
BATTERY_DRAIN_PCT_PER_S_IDLE = 0.01


def build_initial_state(drones: list[Drone], mission: Mission) -> SimulationState:
    """
    Reparte la mision una unica vez al arrancar la simulacion (no se
    re-reparte tick a tick): primero las tareas POINT/DESTINATION por
    proximidad, luego las tareas AREA con los drones que hayan quedado
    libres. La formacion, si la mision la incluye, no se toca aqui: se
    recalcula cada tick en `step` porque su origen (lider/centroide) se
    mueve con el enjambre.
    """
    point_tasks = [t for t in mission.tasks if t.type in (TaskType.POINT, TaskType.DESTINATION)]
    area_tasks = [t for t in mission.tasks if t.type == TaskType.AREA]
    drones_by_id = {d.id: d for d in drones}

    if point_tasks:
        tasks_by_id = {t.id: t for t in point_tasks}
        for drone_id, task_id in assign_point_tasks(drones, point_tasks).items():
            drone = drones_by_id[drone_id]
            drone.assigned_task_id = task_id
            drone.target = tasks_by_id[task_id].points[0]
            drone.status = DroneStatus.EN_ROUTE

    for task in area_tasks:
        unassigned = [d for d in drones if d.assigned_task_id is None]
        for drone_id, route in plan_area_coverage(unassigned, task).items():
            drone = drones_by_id[drone_id]
            drone.assigned_task_id = task.id
            drone.route = route
            drone.target = route[0]
            drone.status = DroneStatus.EN_ROUTE

    return SimulationState(tick=0, drones=drones, conflicts=[])


def step(
    state: SimulationState, mission: Mission, min_separation_m: float = DEFAULT_MIN_SEPARATION_M
) -> SimulationState:
    """Avanza la simulacion un tick y devuelve el nuevo estado (no muta `state`)."""
    next_tick = state.tick + 1
    slot_targets = formation_targets(state.drones, mission.formation) if mission.formation else {}

    new_drones = [
        _advance_drone(drone, slot_targets.get(drone.id, drone.target), state.drones, min_separation_m)
        for drone in state.drones
    ]

    conflicts = detect_conflicts(new_drones, min_separation_m, next_tick)
    return SimulationState(tick=next_tick, drones=new_drones, conflicts=state.conflicts + conflicts)


def run(
    drones: list[Drone], mission: Mission, n_ticks: int, min_separation_m: float = DEFAULT_MIN_SEPARATION_M
) -> list[SimulationState]:
    """Historial completo de estados (tick 0 a n_ticks), para animar o inspeccionar la mision entera."""
    history = [build_initial_state(drones, mission)]
    for _ in range(n_ticks):
        history.append(step(history[-1], mission, min_separation_m))
    return history


def _advance_drone(drone: Drone, target: GeoPoint | None, all_drones: list[Drone], min_separation_m: float) -> Drone:
    if drone.status == DroneStatus.GROUNDED:
        return drone

    if target is None:
        drone.battery_pct = max(0.0, drone.battery_pct - BATTERY_DRAIN_PCT_PER_S_IDLE * TICK_SECONDS)
        return drone

    step_m = drone.speed_mps * TICK_SECONDS
    distance_to_target = haversine_distance_m(drone.position, target)
    north_avoid, east_avoid = separation_offset_m(drone, all_drones, min_separation_m)
    avoiding = (north_avoid, east_avoid) != (0.0, 0.0)

    if distance_to_target <= max(step_m, ARRIVAL_EPSILON_M) and not avoiding:
        drone.position = target
        drone.status = DroneStatus.ON_STATION
        if drone.route:
            drone.route = drone.route[1:]
            if drone.route:
                drone.target = drone.route[0]
                drone.status = DroneStatus.EN_ROUTE
    else:
        move_m = min(step_m, distance_to_target)
        bearing_rad = math.radians(bearing_deg(drone.position, target))
        north = move_m * math.cos(bearing_rad) + north_avoid * step_m
        east = move_m * math.sin(bearing_rad) + east_avoid * step_m
        drone.position = offset_point(drone.position, north, east)
        drone.heading_deg = math.degrees(math.atan2(east, north)) % 360.0
        drone.status = DroneStatus.EN_ROUTE

    drain = BATTERY_DRAIN_PCT_PER_S_MOVING if drone.status == DroneStatus.EN_ROUTE else BATTERY_DRAIN_PCT_PER_S_IDLE
    drone.battery_pct = max(0.0, drone.battery_pct - drain * TICK_SECONDS)
    if drone.battery_pct <= 0.0:
        drone.status = DroneStatus.GROUNDED
    return drone
