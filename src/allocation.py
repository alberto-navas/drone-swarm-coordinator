"""
Reparto de mision explicable: sin aprendizaje automatico, cada decision se
reduce a "que par (dron libre, objetivo sin asignar) esta mas cerca todavia
disponible" — mismo compromiso de simplicidad/explicabilidad que el
emparejamiento vecino-mas-cercano del tracker del proyecto hermano
C-UAS Threat Triage. Es voraz, no globalmente optimo (no se implementa el
algoritmo hungaro): un reparto que minimizase la distancia total del
enjambre completo podria, en algun caso, mejorar a este; se documenta como
limitacion conocida y deliberada, no como descuido.

`greedy_nearest_pairing` es el nucleo reutilizado tanto para repartir
tareas POINT/DESTINATION como, desde src/formation.py, para asignar cada
dron a su hueco de formacion mas cercano: una unica implementacion del
"quien va a donde", no dos.
"""

import math

from src.geo import haversine_distance_m
from src.model import Drone, GeoPoint, Task, TaskType

DEFAULT_SWEEP_LANES = 3


def greedy_nearest_pairing(agents: list[tuple[str, GeoPoint]], targets: list[tuple[str, GeoPoint]]) -> dict[str, str]:
    """
    De todos los pares (agente, objetivo) posibles se elige repetidamente
    el mas cercano todavia disponible, hasta agotar agentes u objetivos.
    Un agente puede acabar emparejado con un objetivo que no es el mas
    cercano a el en particular, si el mas cercano ya se lo llevo, en una
    iteracion anterior, otro agente todavia mas cercano a ese objetivo.
    """
    candidates = sorted(
        ((haversine_distance_m(apos, tpos), aid, tid) for aid, apos in agents for tid, tpos in targets),
        key=lambda c: c[0],
    )
    assigned_agents: set[str] = set()
    assigned_targets: set[str] = set()
    result: dict[str, str] = {}
    for _, aid, tid in candidates:
        if aid in assigned_agents or tid in assigned_targets:
            continue
        result[aid] = tid
        assigned_agents.add(aid)
        assigned_targets.add(tid)
    return result


def assign_point_tasks(drones: list[Drone], tasks: list[Task]) -> dict[str, str]:
    """
    Reparte tareas POINT/DESTINATION entre `drones`, devolviendo
    {drone_id: task_id}. Las tareas se procesan agrupadas por prioridad
    (mayor primero): si hay mas tareas que drones libres, las de mayor
    prioridad se emparejan antes de agotar la flota disponible, en vez de
    dejarlo a la suerte del reparto por distancia global.
    """
    remaining_drones = {d.id: d for d in drones}
    result: dict[str, str] = {}
    for priority in sorted({t.priority for t in tasks}, reverse=True):
        if not remaining_drones:
            break
        group = [t for t in tasks if t.priority == priority]
        pairing = greedy_nearest_pairing(
            agents=[(d.id, d.position) for d in remaining_drones.values()],
            targets=[(t.id, t.points[0]) for t in group],
        )
        for drone_id, task_id in pairing.items():
            result[drone_id] = task_id
            del remaining_drones[drone_id]
    return result


def plan_area_coverage(
    drones: list[Drone], task: Task, sweep_lanes: int = DEFAULT_SWEEP_LANES
) -> dict[str, list[GeoPoint]]:
    """
    Reparte una tarea AREA entre `drones`, devolviendo {drone_id: ruta}.

    El rectangulo definido por las dos esquinas opuestas de `task.points`
    se divide en tantas celdas como drones haya (rejilla filas x columnas
    lo mas cuadrada posible), cada celda se asigna al dron mas cercano a
    su centroide (mismo `greedy_nearest_pairing` de arriba), y a cada dron
    se le entrega una ruta de barrido "cortacesped" (boustrophedon:
    franjas horizontales alternando de sentido) que cubre por completo su
    celda.
    """
    if not drones or task.type != TaskType.AREA:
        return {}

    corner_a, corner_b = task.points[0], task.points[1]
    min_lat, max_lat = sorted((corner_a.lat, corner_b.lat))
    min_lon, max_lon = sorted((corner_a.lon, corner_b.lon))

    n = len(drones)
    cols = math.ceil(math.sqrt(n))
    rows = math.ceil(n / cols)
    cell_lat_span = (max_lat - min_lat) / rows
    cell_lon_span = (max_lon - min_lon) / cols

    cell_bounds: dict[str, tuple[float, float, float, float]] = {}
    cell_centroids: list[tuple[str, GeoPoint]] = []
    cell_index = 0
    for row in range(rows):
        for col in range(cols):
            if cell_index >= n:
                break
            lat0 = min_lat + row * cell_lat_span
            lon0 = min_lon + col * cell_lon_span
            bounds = (lat0, lat0 + cell_lat_span, lon0, lon0 + cell_lon_span)
            cell_id = f"{task.id}-cell-{cell_index}"
            cell_bounds[cell_id] = bounds
            cell_centroids.append((cell_id, GeoPoint(lat=(bounds[0] + bounds[1]) / 2, lon=(bounds[2] + bounds[3]) / 2)))
            cell_index += 1

    pairing = greedy_nearest_pairing(
        agents=[(d.id, d.position) for d in drones],
        targets=cell_centroids,
    )

    routes: dict[str, list[GeoPoint]] = {}
    for drone_id, cell_id in pairing.items():
        lat0, lat1, lon0, lon1 = cell_bounds[cell_id]
        routes[drone_id] = _boustrophedon(lat0, lat1, lon0, lon1, sweep_lanes)
    return routes


def _boustrophedon(lat0: float, lat1: float, lon0: float, lon1: float, lanes: int) -> list[GeoPoint]:
    """Franjas este-oeste igualmente espaciadas dentro de la celda, alternando el sentido en cada franja."""
    route: list[GeoPoint] = []
    for i in range(lanes):
        lane_lat = lat0 + (i + 0.5) * (lat1 - lat0) / lanes
        if i % 2 == 0:
            route.append(GeoPoint(lat=lane_lat, lon=lon0))
            route.append(GeoPoint(lat=lane_lat, lon=lon1))
        else:
            route.append(GeoPoint(lat=lane_lat, lon=lon1))
            route.append(GeoPoint(lat=lane_lat, lon=lon0))
    return route
