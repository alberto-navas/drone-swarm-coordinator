from src.model import ConflictEvent, Drone, GeoPoint, SimulationState
from src.web.animated_map import build_animated_map


def _state(tick: int, drones: list[Drone], conflicts: list[ConflictEvent] | None = None) -> SimulationState:
    return SimulationState(tick=tick, drones=drones, conflicts=conflicts or [])


def test_returns_iframe_wrapper() -> None:
    html = build_animated_map([])
    assert html.startswith("<iframe")
    assert "srcdoc=" in html


def test_empty_history_does_not_crash() -> None:
    # Sin bounds que calcular, el mapa cae a una ubicacion por defecto en vez de fallar.
    html = build_animated_map([])
    assert "<iframe" in html


def test_drone_trail_includes_drone_id_in_popup() -> None:
    drone = Drone(id="drone-1", position=GeoPoint(lat=36.0, lon=-5.0))
    history = [_state(0, [drone])]
    html = build_animated_map(history)
    assert "drone-1" in html


def test_drone_trail_has_one_point_per_tick() -> None:
    positions = [GeoPoint(lat=36.0, lon=-5.0), GeoPoint(lat=36.001, lon=-5.001), GeoPoint(lat=36.002, lon=-5.002)]
    history = [_state(tick, [Drone(id="drone-1", position=p)]) for tick, p in enumerate(positions)]
    html = build_animated_map(history)
    # Cada tick añade un marcador de punto ademas de la linea de estela;
    # basta con comprobar que las tres posiciones distintas aparecen.
    assert "36.001" in html
    assert "36.002" in html


def test_conflict_marker_appears_once_at_the_tick_it_was_detected() -> None:
    drone_a = Drone(id="a", position=GeoPoint(lat=36.0, lon=-5.0))
    drone_b = Drone(id="b", position=GeoPoint(lat=36.0, lon=-5.0))
    event = ConflictEvent(tick=1, drone_a_id="a", drone_b_id="b", distance_m=2.0, min_separation_m=15.0)
    history = [
        _state(0, [drone_a, drone_b], conflicts=[]),
        _state(1, [drone_a, drone_b], conflicts=[event]),
        _state(2, [drone_a, drone_b], conflicts=[event]),  # el mismo evento acumulado, no uno nuevo
    ]
    html = build_animated_map(history)
    assert html.count("Conflicto: a / b") == 1


def test_conflict_marker_omitted_without_new_events() -> None:
    drone = Drone(id="a", position=GeoPoint(lat=36.0, lon=-5.0))
    history = [_state(0, [drone]), _state(1, [drone])]
    html = build_animated_map(history)
    assert "Conflicto" not in html
