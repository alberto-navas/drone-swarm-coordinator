"""
Escenarios de demostracion sintéticos: no existe un dataset publico de
vuelos de enjambre real con el detalle que hace falta aqui (posicion +
tarea + estado de cada dron en cada instante), asi que se generan aqui de
forma deterministica (nada de numeros aleatorios) para poder controlar
exactamente que casos se demuestran, con y sin conflicto de separacion.

Ambos escenarios se plantean sobre la zona del Estrecho de Gibraltar /
Alboran, el mismo area que usa la demo del proyecto hermano
Maritime Domain Awareness: una instalacion portuaria real es un objetivo
de vigilancia/cobertura de area verosimil para este tipo de flota.
"""

from src.geo import offset_point
from src.model import Drone, FormationConfig, FormationShape, GeoPoint, Mission, Task, TaskType

DRONE_COUNT = 10
_PORT_LAUNCH_POINT = GeoPoint(lat=36.140, lon=-5.350)  # cerca de la bahia de Algeciras
_PORT_AREA_SW = GeoPoint(lat=36.100, lon=-5.420)
_PORT_AREA_NE = GeoPoint(lat=36.180, lon=-5.300)
_TRANSIT_START = GeoPoint(lat=36.050, lon=-5.600)


def area_coverage_conflict_scenario(drone_count: int = DRONE_COUNT) -> tuple[list[Drone], Mission]:
    """
    Escenario CON conflicto forzado: los `drone_count` drones despegan
    todos juntos desde el mismo punto de una instalacion portuaria para
    cubrir por completo una zona rectangular alrededor de ella. Al
    arrancar todos en la misma posicion, los primeros ticks generan
    conflictos de separacion reales (distancia inicial 0m entre pares)
    que la correccion reactiva de src/conflict.py tiene que resolver
    mientras cada dron se dirige a la celda que le ha tocado.
    """
    drones = [
        Drone(
            id=f"drone-{i + 1}",
            position=GeoPoint(lat=_PORT_LAUNCH_POINT.lat, lon=_PORT_LAUNCH_POINT.lon),
            speed_mps=15.0,
        )
        for i in range(drone_count)
    ]
    area_task = Task(id="cubrir-puerto", type=TaskType.AREA, points=[_PORT_AREA_SW, _PORT_AREA_NE])
    mission = Mission(id="cobertura-portuaria", tasks=[area_task])
    return drones, mission


def formation_transit_scenario(drone_count: int = DRONE_COUNT) -> tuple[list[Drone], Mission]:
    """
    Escenario SIN conflicto forzado: los `drone_count` drones arrancan ya
    razonablemente separados entre si (una fila este-oeste con 40m de
    separacion) y forman una cuna en V para transitar juntos, para
    demostrar una formacion limpia sin el ruido de una correccion de
    colisiones simultanea arrancando de cero.
    """
    drones = [
        Drone(
            id=f"drone-{i + 1}",
            position=offset_point(_TRANSIT_START, north_m=0.0, east_m=i * 40.0),
            speed_mps=12.0,
            heading_deg=90.0,
        )
        for i in range(drone_count)
    ]
    mission = Mission(
        id="transito-formacion",
        tasks=[],
        formation=FormationConfig(shape=FormationShape.V, spacing_m=30.0),
    )
    return drones, mission


SCENARIOS = {
    "cobertura": area_coverage_conflict_scenario,
    "formacion": formation_transit_scenario,
}
