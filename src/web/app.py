"""
Panel web: ejecuta uno de los escenarios de demostracion incluidos
(src/scenarios.py), o una mision personalizada definida en el propio
formulario, y muestra el resultado en el navegador — mapa animado con la
trayectoria de cada dron y los conflictos de separacion, tabla de estado
final de la flota, y tabla de conflictos detectados.

Capa fina sobre el mismo motor que usa el CLI (src/cli.py): no reimplementa
nada de src/simulation.py, src/allocation.py, src/formation.py ni
src/conflict.py; solo adapta la entrada (parametros de formulario en vez de
argumentos de linea de comandos) y la salida (HTML servido en el navegador
en vez de texto en la terminal).
"""

from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.i18n import UI_LABELS, normalize_lang, scenario_label, status_label
from src.model import ConflictEvent, Drone, FormationConfig, FormationShape, GeoPoint, Mission, Task, TaskType
from src.scenarios import SCENARIOS
from src.simulation import DEFAULT_MIN_SEPARATION_M
from src.simulation import run as run_simulation

from .animated_map import build_animated_map

_TEMPLATES_DIR = Path(__file__).parent / "templates"

_DEFAULT_TICKS = {"cobertura": 60, "formacion": 30}
_MIN_TICKS, _MAX_TICKS = 5, 600
_MIN_DRONES, _MAX_DRONES = 1, 30
_MODES = ("area", "point", "destination", "formation")
_FORMATION_SHAPES = ("line", "v", "grid")

app = FastAPI(title="Drone Swarm Coordinator")
_templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


def _summarize_conflicts(events: list[ConflictEvent]) -> list[dict[str, Any]]:
    """
    Agrupa los eventos de conflicto por pareja de drones para la tabla del
    panel. Dos drones con rutas casi paralelas pueden permanecer dentro
    del radio de seguridad de golpe durante muchos ticks seguidos (el
    motor de simulacion registra un ConflictEvent por tick mientras dure);
    mostrarlos uno a uno inundaria la tabla sin aportar nada que un resumen
    por pareja (desde cuando, cuantas veces, la distancia minima alcanzada)
    no diga ya con mas claridad.
    """
    groups: dict[frozenset[str], list[ConflictEvent]] = {}
    for event in events:
        key = frozenset((event.drone_a_id, event.drone_b_id))
        groups.setdefault(key, []).append(event)

    summaries: list[dict[str, Any]] = [
        {
            "drone_a_id": min(key),
            "drone_b_id": max(key),
            "first_tick": min(e.tick for e in group),
            "last_tick": max(e.tick for e in group),
            "occurrences": len(group),
            "min_distance_m": min(e.distance_m for e in group),
            "min_separation_m": group[0].min_separation_m,
        }
        for key, group in groups.items()
    ]
    summaries.sort(key=lambda s: s["first_tick"])
    return summaries


def _parse_points(text: str) -> list[GeoPoint]:
    """Cada linea no vacia debe ser "lat,lon"; lanza ValueError con un mensaje legible si no."""
    points: list[GeoPoint] = []
    for i, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split(",")
        if len(parts) != 2:
            raise ValueError(f"Linea {i} invalida: '{raw_line}' (se esperaba 'lat,lon')")
        try:
            points.append(GeoPoint(lat=float(parts[0]), lon=float(parts[1])))
        except ValueError as exc:
            raise ValueError(f"Linea {i} invalida: '{raw_line}' (lat/lon deben ser numeros)") from exc
    return points


def _render_report(
    request: Request,
    lang: str,
    mission_label: str,
    base_query: str,
    fleet: list[Drone],
    mission: Mission,
    n_ticks: int,
    min_separation_m: float,
) -> HTMLResponse:
    history = run_simulation(fleet, mission, n_ticks=n_ticks, min_separation_m=min_separation_m)
    final = history[-1]

    context: dict[str, Any] = {
        "lang": lang,
        "labels": UI_LABELS[lang],
        "base_query": base_query,
        "scenario_label": mission_label,
        "n_ticks": n_ticks,
        "map_html": build_animated_map(history),
        # (len(id), id): orden natural para "drone-2" antes que "drone-10".
        "drones": sorted(final.drones, key=lambda d: (len(d.id), d.id)),
        "status_label": lambda status: status_label(status, lang),
        "conflicts": _summarize_conflicts(final.conflicts),
        "conflict_count": len(final.conflicts),
    }
    return _templates.TemplateResponse(request, "report.html", context)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, lang: str = "es") -> HTMLResponse:
    lang = normalize_lang(lang)
    scenarios = [
        {"id": scenario_id, "label": scenario_label(scenario_id, lang), "default_ticks": _DEFAULT_TICKS[scenario_id]}
        for scenario_id in SCENARIOS
    ]
    context = {"lang": lang, "labels": UI_LABELS[lang], "scenarios": scenarios}
    return _templates.TemplateResponse(request, "index.html", context)


@app.get("/run", response_class=HTMLResponse)
async def run_scenario(request: Request, scenario: str, ticks: int | None = None, lang: str = "es") -> HTMLResponse:
    lang = normalize_lang(lang)
    if scenario not in SCENARIOS:
        raise HTTPException(status_code=404, detail=f"Escenario desconocido: {scenario}")
    n_ticks = _DEFAULT_TICKS[scenario] if ticks is None else max(_MIN_TICKS, min(_MAX_TICKS, ticks))

    fleet, mission = SCENARIOS[scenario]()
    base_query = f"/run?scenario={scenario}&ticks={n_ticks}"
    return _render_report(
        request, lang, scenario_label(scenario, lang), base_query, fleet, mission, n_ticks, DEFAULT_MIN_SEPARATION_M
    )


@app.get("/plan", response_class=HTMLResponse)
async def plan_mission(
    request: Request,
    drones: int = 6,
    launch_lat: float = 36.140,
    launch_lon: float = -5.350,
    mode: str = "area",
    points: str = "",
    area_sw_lat: float = 36.100,
    area_sw_lon: float = -5.420,
    area_ne_lat: float = 36.180,
    area_ne_lon: float = -5.300,
    formation_shape: str = "line",
    spacing_m: float = 25.0,
    leader: str = "",
    ticks: int = 45,
    min_separation: float = DEFAULT_MIN_SEPARATION_M,
    lang: str = "es",
) -> HTMLResponse:
    """
    Construye una Mission a partir de los parametros del formulario y la
    simula igual que un escenario de demo. `mode` decide que bloque de
    parametros se usa — una mision es de tarea (area/puntos/destinos) O de
    formacion, nunca ambas: la formacion recalcula el objetivo de CADA
    dron en cada tick (ver src/simulation.step), asi que combinarla con
    tareas dejaria las tareas sin ningun efecto visible, silenciosamente.
    Mejor un unico modo honesto que una opcion combinada enganosa.
    """
    lang = normalize_lang(lang)
    if mode not in _MODES:
        raise HTTPException(status_code=400, detail=f"Tipo de mision desconocido: {mode}")
    drone_count = max(_MIN_DRONES, min(_MAX_DRONES, drones))
    n_ticks = max(_MIN_TICKS, min(_MAX_TICKS, ticks))

    tasks: list[Task] = []
    formation_config: FormationConfig | None = None

    if mode in ("point", "destination"):
        try:
            task_points = _parse_points(points)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if not task_points:
            raise HTTPException(status_code=400, detail="Indica al menos un punto (una linea 'lat,lon').")
        kind = TaskType.POINT if mode == "point" else TaskType.DESTINATION
        tasks = [Task(id=f"tarea-{i + 1}", type=kind, points=[p]) for i, p in enumerate(task_points)]
    elif mode == "area":
        tasks = [
            Task(
                id="area-personalizada",
                type=TaskType.AREA,
                points=[GeoPoint(lat=area_sw_lat, lon=area_sw_lon), GeoPoint(lat=area_ne_lat, lon=area_ne_lon)],
            )
        ]
    else:  # formation
        if formation_shape not in _FORMATION_SHAPES:
            raise HTTPException(status_code=400, detail=f"Formacion desconocida: {formation_shape}")
        leader_id = leader.strip() or None
        if leader_id is not None and leader_id not in {f"drone-{i + 1}" for i in range(drone_count)}:
            raise HTTPException(
                status_code=400,
                detail=f"'{leader_id}' no es un dron valido (usa drone-1 .. drone-{drone_count}).",
            )
        formation_config = FormationConfig(
            shape=FormationShape(formation_shape), spacing_m=spacing_m, leader_id=leader_id
        )

    fleet = [
        Drone(id=f"drone-{i + 1}", position=GeoPoint(lat=launch_lat, lon=launch_lon), speed_mps=12.0)
        for i in range(drone_count)
    ]
    mission = Mission(id="mision-personalizada", tasks=tasks, formation=formation_config)

    base_query = "/plan?" + urlencode(
        {
            "drones": drone_count,
            "launch_lat": launch_lat,
            "launch_lon": launch_lon,
            "mode": mode,
            "points": points,
            "area_sw_lat": area_sw_lat,
            "area_sw_lon": area_sw_lon,
            "area_ne_lat": area_ne_lat,
            "area_ne_lon": area_ne_lon,
            "formation_shape": formation_shape,
            "spacing_m": spacing_m,
            "leader": leader,
            "ticks": n_ticks,
            "min_separation": min_separation,
        }
    )
    return _render_report(
        request, lang, UI_LABELS[lang]["custom_mission_label"], base_query, fleet, mission, n_ticks, min_separation
    )
