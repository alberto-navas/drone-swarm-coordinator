"""
Panel web: ejecuta uno de los escenarios de demostracion incluidos
(src/scenarios.py) y muestra el resultado en el navegador — mapa animado
con la trayectoria de cada dron y los conflictos de separacion, tabla de
estado final de la flota, y tabla de conflictos detectados.

Capa fina sobre el mismo motor que usa el CLI (src/cli.py): no reimplementa
nada de src/simulation.py, src/allocation.py, src/formation.py ni
src/conflict.py; solo adapta la salida (HTML servido en el navegador en vez
de texto en la terminal).
"""

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.model import ConflictEvent
from src.scenarios import SCENARIOS
from src.simulation import DEFAULT_MIN_SEPARATION_M
from src.simulation import run as run_simulation

from .animated_map import build_animated_map

_TEMPLATES_DIR = Path(__file__).parent / "templates"

_SCENARIO_LABELS = {
    "cobertura": "Cobertura de area con conflicto forzado",
    "formacion": "Transito en formacion (sin conflicto forzado)",
}
_DEFAULT_TICKS = {"cobertura": 60, "formacion": 30}
_MIN_TICKS, _MAX_TICKS = 5, 600

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


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    scenarios = [
        {"id": scenario_id, "label": _SCENARIO_LABELS[scenario_id], "default_ticks": _DEFAULT_TICKS[scenario_id]}
        for scenario_id in SCENARIOS
    ]
    return _templates.TemplateResponse(request, "index.html", {"scenarios": scenarios})


@app.get("/run", response_class=HTMLResponse)
async def run_scenario(request: Request, scenario: str, ticks: int | None = None) -> HTMLResponse:
    if scenario not in SCENARIOS:
        raise HTTPException(status_code=404, detail=f"Escenario desconocido: {scenario}")
    n_ticks = _DEFAULT_TICKS[scenario] if ticks is None else max(_MIN_TICKS, min(_MAX_TICKS, ticks))

    drones, mission = SCENARIOS[scenario]()
    history = run_simulation(drones, mission, n_ticks=n_ticks, min_separation_m=DEFAULT_MIN_SEPARATION_M)
    final = history[-1]

    context: dict[str, Any] = {
        "scenario_label": _SCENARIO_LABELS[scenario],
        "n_ticks": n_ticks,
        "map_html": build_animated_map(history),
        # (len(id), id): orden natural para "drone-2" antes que "drone-10".
        "drones": sorted(final.drones, key=lambda d: (len(d.id), d.id)),
        "conflicts": _summarize_conflicts(final.conflicts),
        "conflict_count": len(final.conflicts),
    }
    return _templates.TemplateResponse(request, "report.html", context)
