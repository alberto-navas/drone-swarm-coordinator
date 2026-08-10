from src.i18n import SUPPORTED_LANGS, UI_LABELS, cli_label, normalize_lang, scenario_label, status_label


def test_normalize_lang_keeps_supported_languages() -> None:
    for lang in SUPPORTED_LANGS:
        assert normalize_lang(lang) == lang


def test_normalize_lang_falls_back_to_spanish() -> None:
    assert normalize_lang("fr") == "es"
    assert normalize_lang(None) == "es"


def test_status_label_translates_known_status() -> None:
    assert status_label("en_route", "es") == "en ruta"
    assert status_label("en_route", "en") == "en route"
    assert status_label("en_route", "de") == "unterwegs"


def test_status_label_falls_back_to_raw_value_for_unknown_status() -> None:
    assert status_label("mystery", "en") == "mystery"


def test_scenario_label_translates_known_scenario() -> None:
    assert scenario_label("cobertura", "en") == "Area coverage with a forced conflict"
    assert scenario_label("formacion", "de").startswith("Formationsflug")


def test_scenario_label_falls_back_to_id_for_unknown_scenario() -> None:
    assert scenario_label("no-existe", "en") == "no-existe"


def test_cli_label_has_same_keys_across_languages() -> None:
    keys_es = {"mission", "drones", "tick", "conflicts_detected", "status", "battery", "position", "task"}
    for lang in SUPPORTED_LANGS:
        for key in keys_es:
            assert cli_label(key, lang)  # no lanza KeyError y no esta vacio


def test_ui_labels_have_identical_keys_across_languages() -> None:
    es_keys = set(UI_LABELS["es"])
    for lang in SUPPORTED_LANGS:
        assert set(UI_LABELS[lang]) == es_keys
