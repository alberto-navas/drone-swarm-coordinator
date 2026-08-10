"""
Punto de entrada de linea de comandos: ejecuta un escenario de
demostracion y muestra el estado final de la flota.

Ejemplo de uso:
    python -m src.cli cobertura
    python -m src.cli formacion --ticks 30
    python -m src.cli formacion --lang en
"""

import argparse

from src.i18n import cli_label, normalize_lang, status_label
from src.model import SimulationState
from src.scenarios import SCENARIOS
from src.simulation import DEFAULT_MIN_SEPARATION_M, run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Simula un escenario de coordinacion de un enjambre de drones propios "
            "(reparto de mision, formacion, evitacion de colisiones) y muestra el "
            "estado final de la flota. Es una herramienta de planificacion y "
            "visualizacion: no controla drones reales ni se conecta a hardware."
        )
    )
    parser.add_argument("scenario", choices=sorted(SCENARIOS), help="Escenario de demostracion a ejecutar.")
    parser.add_argument(
        "--ticks", type=int, default=60, help="Numero de pasos de simulacion (1 tick = 1 segundo). Por defecto: 60."
    )
    parser.add_argument(
        "--min-separation",
        type=float,
        default=DEFAULT_MIN_SEPARATION_M,
        dest="min_separation_m",
        help=f"Separacion minima de seguridad entre drones, en metros. Por defecto: {DEFAULT_MIN_SEPARATION_M}.",
    )
    parser.add_argument("--lang", choices=["es", "en", "de"], default="es", help="Idioma del informe. Por defecto: es.")
    args = parser.parse_args(argv)

    drones, mission = SCENARIOS[args.scenario]()
    history = run(drones, mission, n_ticks=args.ticks, min_separation_m=args.min_separation_m)
    _print_report(history[-1], mission.id, normalize_lang(args.lang))
    return 0


def _print_report(final: SimulationState, mission_id: str, lang: str) -> None:
    print(
        f"{cli_label('mission', lang)}: {mission_id}  ({len(final.drones)} {cli_label('drones', lang)}, "
        f"{cli_label('tick', lang)} {final.tick})"
    )
    print(f"{cli_label('conflicts_detected', lang)}: {len(final.conflicts)}")
    print()
    # (len(id), id) en vez de solo id: orden natural para "drone-2" antes que
    # "drone-10" (compararlos como texto los pondria al reves).
    for drone in sorted(final.drones, key=lambda d: (len(d.id), d.id)):
        print(
            f"  {drone.id:10s} {cli_label('status', lang)}={status_label(drone.status.value, lang):11s} "
            f"{cli_label('battery', lang)}={drone.battery_pct:5.1f}%  "
            f"{cli_label('position', lang)}=({drone.position.lat:.5f}, {drone.position.lon:.5f})  "
            f"{cli_label('task', lang)}={drone.assigned_task_id or '-'}"
        )


if __name__ == "__main__":
    raise SystemExit(main())
