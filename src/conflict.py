"""
Deteccion y correccion de colisiones entre drones propios.

Deteccion: en cada paso de simulacion se calcula la distancia entre cada
par de drones y se registra un ConflictEvent si cae por debajo del umbral
de separacion minima de seguridad.

Correccion: vector de repulsion tipo "separation steering" (regla clasica
de boids, Reynolds 1987) que src/simulation.py suma al vector de avance
hacia la tarea/hueco de formacion de cada dron cuando otro invade su radio
de seguridad. No es un optimizador de trayectorias ni ofrece garantia
matematica de evitar colisiones (no hay reciprocal velocity obstacles ni
campos potenciales completos): es una regla reactiva simple y explicable,
suficiente para una demo y documentada como tal en el README.
"""

import math

from src.geo import bearing_deg, haversine_distance_m
from src.model import ConflictEvent, Drone


def detect_conflicts(drones: list[Drone], min_separation_m: float, tick: int) -> list[ConflictEvent]:
    """Un ConflictEvent por cada par de drones mas cerca entre si que `min_separation_m`."""
    events: list[ConflictEvent] = []
    for i, a in enumerate(drones):
        for b in drones[i + 1 :]:
            distance = haversine_distance_m(a.position, b.position)
            if distance < min_separation_m:
                events.append(
                    ConflictEvent(
                        tick=tick,
                        drone_a_id=a.id,
                        drone_b_id=b.id,
                        distance_m=distance,
                        min_separation_m=min_separation_m,
                    )
                )
    return events


def separation_offset_m(drone: Drone, others: list[Drone], min_separation_m: float) -> tuple[float, float]:
    """
    Vector de repulsion (norte_m, este_m) para `drone`: suma de una
    componente por cada otro dron que invada su radio de seguridad,
    apuntando en la direccion opuesta a ese dron y con magnitud
    proporcional a cuanto invade el radio (cuanto mas cerca, mas fuerte
    empuja). (0, 0) si ningun otro dron esta mas cerca que
    `min_separation_m`.
    """
    north = east = 0.0
    for other in others:
        if other.id == drone.id:
            continue
        distance = haversine_distance_m(drone.position, other.position)
        if distance >= min_separation_m:
            continue
        escape_bearing_rad = math.radians(bearing_deg(other.position, drone.position))
        strength = (min_separation_m - distance) / min_separation_m
        north += strength * math.cos(escape_bearing_rad)
        east += strength * math.sin(escape_bearing_rad)
    return north, east
