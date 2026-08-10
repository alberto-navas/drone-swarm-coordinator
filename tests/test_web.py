"""
Tests del panel web (src/web/app.py), usando el TestClient de FastAPI (no
levanta un servidor real, invoca la app directamente en el mismo proceso).
"""

from fastapi.testclient import TestClient

from src.model import ConflictEvent
from src.web.app import _summarize_conflicts, app

client = TestClient(app)


def test_summarize_conflicts_groups_repeated_pair_regardless_of_order() -> None:
    events = [
        ConflictEvent(tick=1, drone_a_id="drone-1", drone_b_id="drone-2", distance_m=9.0, min_separation_m=15.0),
        ConflictEvent(tick=2, drone_a_id="drone-2", drone_b_id="drone-1", distance_m=4.0, min_separation_m=15.0),
        ConflictEvent(tick=3, drone_a_id="drone-1", drone_b_id="drone-2", distance_m=7.0, min_separation_m=15.0),
    ]
    summaries = _summarize_conflicts(events)
    assert len(summaries) == 1
    summary = summaries[0]
    assert {summary["drone_a_id"], summary["drone_b_id"]} == {"drone-1", "drone-2"}
    assert summary["first_tick"] == 1
    assert summary["last_tick"] == 3
    assert summary["occurrences"] == 3
    assert summary["min_distance_m"] == 4.0


def test_summarize_conflicts_keeps_different_pairs_separate() -> None:
    events = [
        ConflictEvent(tick=1, drone_a_id="a", drone_b_id="b", distance_m=5.0, min_separation_m=15.0),
        ConflictEvent(tick=1, drone_a_id="c", drone_b_id="d", distance_m=6.0, min_separation_m=15.0),
    ]
    summaries = _summarize_conflicts(events)
    assert len(summaries) == 2


def test_summarize_conflicts_empty_list_is_empty() -> None:
    assert _summarize_conflicts([]) == []


def test_index_renders_both_scenarios() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "<form" in response.text
    assert "scenario" in response.text
    assert "cobertura" in response.text
    assert "formacion" in response.text


def test_run_coverage_scenario_renders_report() -> None:
    response = client.get("/run", params={"scenario": "cobertura", "ticks": 10})
    assert response.status_code == 200
    assert "<iframe" in response.text
    assert "drone-1" in response.text


def test_run_formation_scenario_renders_report() -> None:
    response = client.get("/run", params={"scenario": "formacion", "ticks": 10})
    assert response.status_code == 200
    assert "<iframe" in response.text


def test_run_uses_scenario_default_ticks_when_not_given() -> None:
    response = client.get("/run", params={"scenario": "formacion"})
    assert response.status_code == 200
    assert "30" in response.text  # ticks por defecto de "formacion"


def test_run_clamps_ticks_to_allowed_range() -> None:
    response = client.get("/run", params={"scenario": "formacion", "ticks": 10_000})
    assert response.status_code == 200
    assert "600" in response.text  # se recorta al maximo permitido


def test_run_unknown_scenario_returns_404() -> None:
    response = client.get("/run", params={"scenario": "no-existe"})
    assert response.status_code == 404


def test_run_shows_no_conflicts_message_when_there_are_none() -> None:
    # Un escenario de formacion muy corto (5 ticks) no da tiempo a que los
    # drones, que arrancan ya separados, lleguen a invadir el radio de
    # seguridad de ningun otro.
    response = client.get("/run", params={"scenario": "formacion", "ticks": 5})
    assert response.status_code == 200
    assert "No se detecto ningun conflicto" in response.text


def test_main_module_is_importable() -> None:
    """src/web/__main__.py solo se ejecuta con `python -m src.web`; esto solo comprueba que sus imports no fallan."""
    import src.web.__main__  # noqa: F401
