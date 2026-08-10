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


def test_index_defaults_to_spanish() -> None:
    response = client.get("/")
    assert 'lang="es"' in response.text
    assert "Coordinacion de un enjambre" in response.text


def test_index_lang_query_param_switches_language() -> None:
    en = client.get("/?lang=en")
    de = client.get("/?lang=de")
    assert 'lang="en"' in en.text and "Coordinating a swarm" in en.text
    assert 'lang="de"' in de.text and "Koordination eines eigenen" in de.text


def test_index_unsupported_lang_falls_back_to_spanish() -> None:
    response = client.get("/?lang=fr")
    assert 'lang="es"' in response.text


def test_run_translates_report_when_lang_given() -> None:
    response = client.get("/run", params={"scenario": "formacion", "ticks": 10, "lang": "en"})
    assert response.status_code == 200
    assert 'lang="en"' in response.text
    assert "Final fleet status" in response.text
    assert "Area coverage" not in response.text  # es el escenario "formacion", no "cobertura"


def test_run_translates_status_badges() -> None:
    response = client.get("/run", params={"scenario": "formacion", "ticks": 1, "lang": "de"})
    assert response.status_code == 200
    assert "unterwegs" in response.text or "in Position" in response.text


def test_run_lang_switch_preserves_scenario_and_ticks() -> None:
    response = client.get("/run", params={"scenario": "cobertura", "ticks": 15, "lang": "es"})
    # "&" sale escapado como "&amp;" en el HTML (correcto dentro de un atributo href).
    assert "/run?scenario=cobertura&amp;ticks=15&lang=en" in response.text


def test_index_shows_custom_mission_form() -> None:
    response = client.get("/")
    assert 'action="/plan"' in response.text
    assert 'name="mode"' in response.text


def test_plan_area_mission_renders_report() -> None:
    response = client.get(
        "/plan",
        params={
            "drones": 4,
            "launch_lat": 36.14,
            "launch_lon": -5.35,
            "mode": "area",
            "area_sw_lat": 36.10,
            "area_sw_lon": -5.42,
            "area_ne_lat": 36.18,
            "area_ne_lon": -5.30,
            "ticks": 5,
        },
    )
    assert response.status_code == 200
    assert "<iframe" in response.text
    assert "drone-1" in response.text
    assert "drone-4" in response.text


def test_plan_point_mission_uses_given_points() -> None:
    response = client.get(
        "/plan",
        params={"drones": 2, "mode": "point", "points": "36.15,-5.36\n36.13,-5.34", "ticks": 5},
    )
    assert response.status_code == 200
    assert "<iframe" in response.text


def test_plan_destination_mission_works() -> None:
    response = client.get(
        "/plan",
        params={"drones": 1, "mode": "destination", "points": "36.15,-5.36", "ticks": 5},
    )
    assert response.status_code == 200


def test_plan_formation_mission_ignores_points() -> None:
    response = client.get(
        "/plan",
        params={"drones": 5, "mode": "formation", "formation_shape": "v", "spacing_m": 20, "ticks": 10},
    )
    assert response.status_code == 200
    assert "<iframe" in response.text


def test_plan_formation_with_valid_leader() -> None:
    response = client.get(
        "/plan",
        params={"drones": 3, "mode": "formation", "formation_shape": "grid", "leader": "drone-2", "ticks": 5},
    )
    assert response.status_code == 200


def test_plan_formation_with_invalid_leader_returns_400() -> None:
    response = client.get(
        "/plan",
        params={"drones": 3, "mode": "formation", "leader": "drone-99", "ticks": 5},
    )
    assert response.status_code == 400


def test_plan_unknown_mode_returns_400() -> None:
    response = client.get("/plan", params={"mode": "no-existe"})
    assert response.status_code == 400


def test_plan_unknown_formation_shape_returns_400() -> None:
    response = client.get("/plan", params={"mode": "formation", "formation_shape": "no-existe"})
    assert response.status_code == 400


def test_plan_point_mission_without_points_returns_400() -> None:
    response = client.get("/plan", params={"mode": "point", "points": ""})
    assert response.status_code == 400


def test_plan_point_mission_with_malformed_line_returns_400() -> None:
    response = client.get("/plan", params={"mode": "point", "points": "esto no es un punto"})
    assert response.status_code == 400
    assert "Linea 1" in response.json()["detail"]


def test_plan_clamps_drone_count_and_ticks() -> None:
    response = client.get("/plan", params={"drones": 999, "ticks": 999_999, "mode": "area"})
    assert response.status_code == 200
    assert "drone-30" in response.text  # se recorta al maximo de 30 drones
    assert "drone-31" not in response.text


def test_plan_report_label_is_custom_mission() -> None:
    response = client.get("/plan", params={"mode": "area", "ticks": 5, "lang": "en"})
    assert "Custom mission" in response.text


def test_plan_lang_switch_preserves_query() -> None:
    response = client.get("/plan", params={"mode": "formation", "drones": 3, "ticks": 5, "lang": "es"})
    assert "mode=formation" in response.text
    assert "&lang=en" in response.text


def test_main_module_is_importable() -> None:
    """src/web/__main__.py solo se ejecuta con `python -m src.web`; esto solo comprueba que sus imports no fallan."""
    import src.web.__main__  # noqa: F401
