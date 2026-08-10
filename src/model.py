"""
Modelo de datos comun del proyecto.

El enjambre vive en coordenadas geograficas reales (WGS84), igual que el
proyecto hermano de Maritime Domain Awareness, para que una mision se
pueda plantear sobre un area de operacion real (cubrir un tramo de costa,
vigilar unas instalaciones) en vez de un espacio abstracto. La geometria de
corta escala (separacion entre drones, offsets de formacion) se resuelve
con la aproximacion de plano tangente local de src/geo.py.

Todo el pipeline (reparto, formacion, deteccion de conflictos, simulacion)
es agnostico a como se haya construido la mision: solo ve
Drone / Task / Mission / SimulationState.
"""

from dataclasses import dataclass, field
from enum import StrEnum


class TaskType(StrEnum):
    """Tipo de tarea de mision. Cada tipo usa una estrategia de reparto distinta (src/allocation.py)."""

    POINT = "point"  # vigilar un punto fijo (loiter)
    DESTINATION = "destination"  # llegar a un destino y permanecer
    AREA = "area"  # cubrir por completo una zona rectangular


class DroneStatus(StrEnum):
    IDLE = "idle"  # sin tarea asignada
    EN_ROUTE = "en_route"  # desplazandose hacia su tarea/hueco de formacion
    ON_STATION = "on_station"  # ha llegado y esta cumpliendo su tarea (o en formacion, en posicion)
    GROUNDED = "grounded"  # bateria agotada, fuera de servicio


class FormationShape(StrEnum):
    LINE = "line"  # una fila perpendicular al rumbo del grupo
    V = "v"  # cuna clasica, dos brazos hacia atras desde el lider
    GRID = "grid"  # rejilla de filas x columnas


@dataclass
class GeoPoint:
    lat: float
    lon: float


@dataclass
class Task:
    id: str
    type: TaskType
    # POINT/DESTINATION: un unico punto (points[0]). AREA: las dos esquinas
    # opuestas del rectangulo a cubrir.
    points: list[GeoPoint]
    # Desempata el reparto cuando hay mas tareas POINT/DESTINATION que
    # drones libres: se sirven primero las de prioridad mas alta.
    priority: int = 1


@dataclass
class Drone:
    id: str
    position: GeoPoint
    heading_deg: float = 0.0  # rumbo actual, 0 = norte, sentido horario
    speed_mps: float = 12.0  # velocidad de crucero, metros/segundo
    battery_pct: float = 100.0
    status: DroneStatus = DroneStatus.IDLE
    assigned_task_id: str | None = None
    # Punto inmediato hacia el que se dirige ahora mismo. Para una tarea
    # POINT/DESTINATION es fijo una vez asignado; para AREA se va
    # actualizando a medida que se completa la ruta de barrido (`route`);
    # para formacion se recalcula cada tick porque el hueco se mueve con el
    # lider/centroide.
    target: GeoPoint | None = None
    # Puntos de barrido pendientes (solo se usa en tareas AREA); `target`
    # siempre refleja route[0] mientras route no este vacia.
    route: list[GeoPoint] = field(default_factory=list)


@dataclass
class FormationConfig:
    shape: FormationShape
    spacing_m: float = 25.0
    # None = la formacion se centra en el centroide del grupo y usa su
    # rumbo medio; si se indica, el hueco de cada dron se calcula relativo
    # a la posicion/rumbo de ese dron concreto.
    leader_id: str | None = None


@dataclass
class Mission:
    id: str
    tasks: list[Task]
    formation: FormationConfig | None = None


@dataclass
class ConflictEvent:
    tick: int
    drone_a_id: str
    drone_b_id: str
    distance_m: float
    min_separation_m: float


@dataclass
class SimulationState:
    tick: int
    drones: list[Drone]
    conflicts: list[ConflictEvent] = field(default_factory=list)
