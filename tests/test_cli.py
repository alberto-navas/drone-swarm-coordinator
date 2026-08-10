from src.cli import main


def test_main_runs_area_coverage_scenario_and_prints_report(capsys) -> None:
    exit_code = main(["cobertura", "--ticks", "5"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "Mision: cobertura-portuaria" in out
    assert "drone-1" in out


def test_main_runs_formation_scenario_and_prints_report(capsys) -> None:
    exit_code = main(["formacion", "--ticks", "5"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "Mision: transito-formacion" in out


def test_main_rejects_unknown_scenario() -> None:
    try:
        main(["no-existe"])
        raise AssertionError("se esperaba SystemExit")
    except SystemExit as exc:
        assert exc.code != 0
