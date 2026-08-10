"""
Formaciones (linea, V, rejilla) relativas a un lider o al centroide del
grupo.

Los huecos se calculan en un sistema local "adelante/al lado" del rumbo del
grupo y se rotan a norte/este antes de convertirlos a lat/lon
(src/geo.offset_point). Cada dron se empareja con su hueco mas cercano
mediante `greedy_nearest_pairing` (src/allocation.py) en vez de asignarlos
en el orden en que llegan, para no cruzar trayectorias innecesariamente
cuando dos drones podrian intercambiarse de hueco con menos desplazamiento
total.

`formation_targets` se llama una vez por tick (src/simulation.py) porque el
origen de la formacion (lider o centroide) se mueve.
"""

import math

from src.allocation import greedy_nearest_pairing
from src.geo import centroid, offset_point
from src.model import Drone, FormationConfig, FormationShape, GeoPoint


def formation_targets(drones: list[Drone], config: FormationConfig) -> dict[str, GeoPoint]:
    """Hueco de formacion absoluto asignado a cada dron para el instante actual."""
    if not drones:
        return {}
    origin, heading_deg = _group_origin_and_heading(drones, config.leader_id)
    slots = _compute_slots(len(drones), config, origin, heading_deg)
    pairing = greedy_nearest_pairing(
        agents=[(d.id, d.position) for d in drones],
        targets=list(slots.items()),
    )
    return {drone_id: slots[slot_id] for drone_id, slot_id in pairing.items()}


def _group_origin_and_heading(drones: list[Drone], leader_id: str | None) -> tuple[GeoPoint, float]:
    if leader_id is not None:
        leader = next(d for d in drones if d.id == leader_id)
        return leader.position, leader.heading_deg
    origin = centroid([d.position for d in drones])
    heading = _mean_heading_deg([d.heading_deg for d in drones])
    return origin, heading


def _mean_heading_deg(headings: list[float]) -> float:
    """Media circular (no aritmetica: 350 y 10 grados deben promediar a 0, no a 180)."""
    sin_sum = sum(math.sin(math.radians(h)) for h in headings)
    cos_sum = sum(math.cos(math.radians(h)) for h in headings)
    # Doble modulo: ver el comentario equivalente en src/geo.bearing_deg.
    return (math.degrees(math.atan2(sin_sum, cos_sum)) % 360.0) % 360.0


def _compute_slots(n: int, config: FormationConfig, origin: GeoPoint, heading_deg: float) -> dict[str, GeoPoint]:
    heading_rad = math.radians(heading_deg)
    slots: dict[str, GeoPoint] = {}
    for i, (forward_m, side_m) in enumerate(_local_offsets(config.shape, n, config.spacing_m)):
        north_m = forward_m * math.cos(heading_rad) - side_m * math.sin(heading_rad)
        east_m = forward_m * math.sin(heading_rad) + side_m * math.cos(heading_rad)
        slots[f"slot-{i}"] = offset_point(origin, north_m, east_m)
    return slots


def _local_offsets(shape: FormationShape, n: int, spacing_m: float) -> list[tuple[float, float]]:
    """(adelante, lado) en metros de cada hueco, antes de rotar por el rumbo del grupo.

    adelante > 0 = por delante del origen.
    """
    if shape == FormationShape.LINE:
        return [(0.0, (i - (n - 1) / 2) * spacing_m) for i in range(n)]

    if shape == FormationShape.V:
        # La punta de la cuna (indice 0) coincide con el origen; el resto
        # se reparte alternando brazo derecho/izquierdo, cada vez un paso
        # mas atras y mas hacia el lado.
        offsets: list[tuple[float, float]] = [(0.0, 0.0)]
        arm = 1
        side = 1
        while len(offsets) < n:
            offsets.append((-arm * spacing_m, side * arm * spacing_m))
            side *= -1
            if side == 1:
                arm += 1
        return offsets[:n]

    if shape == FormationShape.GRID:
        cols = math.ceil(math.sqrt(n))
        return [(-(i // cols) * spacing_m, ((i % cols) - (cols - 1) / 2) * spacing_m) for i in range(n)]

    raise ValueError(f"forma de formacion desconocida: {shape}")
