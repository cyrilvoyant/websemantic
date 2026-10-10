"""Web app conversation logic (webapp/glue.py): reproductions of the review counter-examples.

The language model's reading is injected as JSON, as the relay would return it; `run` is replaced by a marker so
that the decision itself is tested (whether the pinned code would be called), except where real native outputs
are needed. Only TLS and LQL-Equiv compute; nothing here changes their equations.
"""

import importlib
import json
import os
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
os.environ["WEBSEMANTIC_WS"] = str(ROOT)
sys.path.insert(0, str(ROOT / "webapp"))
sys.path.insert(0, str(ROOT / "tools"))
glue = importlib.import_module("glue")
TLS_TASK = glue.SINGLE_TASK["tls"]
LQL_TASK = glue.SINGLE_TASK["lql"]


@pytest.fixture
def calls(monkeypatch):
    seen = []

    def marker(model, state, lang):
        seen.append(model)
        return {"kind": model, "marker": True}

    monkeypatch.setattr(glue, "run", marker)
    return seen


def turn(model, state, message, parsed=None, lang="fr"):
    out = json.loads(glue.api_turn(model, lang, json.dumps(state), message,
                                   "" if parsed is None else json.dumps(parsed)))
    return out, out["state"]


def reading(task, *values, message="Message lu."):
    return {"task": task, "values": list(values), "questions": [], "message": message}


def proposed_tls(calls):
    state = json.loads(glue.api_fresh("tls", "fr"))
    out, state = turn("tls", state, "Un tunnel de 2 km.",
                      reading(TLS_TASK, {"field": "length_m", "value": 2000, "unit": "m", "origin": "provided",
                                         "evidence": "2 km"}))
    assert out["decision"] == "clarify" and not calls
    return state


def accepted_tls(calls):
    state = proposed_tls(calls)
    out, state = turn("tls", state, "oui")
    assert out["decision"] == "execute" and calls == ["tls"]
    calls.clear()
    return state


# ------------------------------------------------------------ consent


@pytest.mark.parametrize("message,lang", [("oui seulement pour la période simulée", "fr"),
                                          ("yes, only the simulated period", "en")])
def test_partial_consent_accepts_only_the_named_field(calls, message, lang):
    state = proposed_tls(calls)
    out, state = turn("tls", state, message, reading(TLS_TASK), lang=lang)
    assert out["decision"] == "clarify" and not calls
    assert state["experiment"]["n_days"]["accepted"] is True
    assert state["experiment"]["n_runs"]["accepted"] is False
    assert state["inputs"]["altitude_m"]["accepted"] is False


def test_partial_consent_by_a_short_word_ignores_a_restated_value(calls):
    """Browser retest: 'oui, mais seulement pour la longueur' after two proposed conventions."""
    state = json.loads(glue.api_fresh("tls", "fr"))
    msg = "Un tunnel long avec beaucoup de trafic"
    out, state = turn("tls", state, msg, reading(
        TLS_TASK, {"field": "length_m", "origin": "convention", "evidence": "tunnel long", "level": "long"},
        {"field": "traffic_level", "origin": "convention", "evidence": "beaucoup de trafic", "level": "high"}))
    assert state["inputs"]["length_m"]["accepted"] is False and not calls
    out, state = turn("tls", state, "oui, mais seulement pour la longueur", reading(
        TLS_TASK, {"field": "length_m", "value": state["inputs"]["length_m"]["value"], "unit": "m",
                   "origin": "provided", "evidence": "9000 mètres"}, message="La longueur est fixée."))
    assert state["inputs"]["length_m"]["accepted"] is True and state["inputs"]["length_m"]["origin"] == "assumption"
    assert state["inputs"]["traffic_level"]["accepted"] is False
    assert "Je n'ai pas pu utiliser" not in out["reply"] and out["decision"] == "clarify" and not calls


def test_two_readings_for_one_field_use_neither(calls):
    """Browser retest: 'Prostate, rectum comme organe à risque' read as organ=Prostate then organ=Rectum."""
    state = json.loads(glue.api_fresh("lql", "fr"))
    msg = "Prostate, rectum comme organe à risque, 20 séances de 3 Gy, sans interruption."
    out, after = turn("lql", state, msg, reading(
        LQL_TASK, {"field": "organ", "value": "Prostate", "origin": "provided", "evidence": "Prostate"},
        {"field": "organ", "value": "Rectum", "origin": "provided", "evidence": "rectum"},
        {"field": "gap_days", "value": 0, "unit": "unit:DAY", "origin": "provided", "evidence": "sans interruption"}))
    assert "organ" not in after["inputs"] and "deux lectures différentes" in out["reply"]
    assert after["inputs"]["gap_days"]["value"] == 0 and after["inputs"]["gap_days"]["origin"] == "provided"
    assert out["decision"] == "clarify" and not calls


def test_reading_context_lists_the_library_categories():
    lql = json.loads((ROOT / "webapp" / "llm" / "lql.json").read_text(encoding="utf-8"))
    cats = {p["field"]: p["categories"] for p in lql["params"]}
    assert "Rectum" in cats["organ"] and "Prostate" in cats["tumour_site"] and "Prostate" not in cats["organ"]


def test_the_model_sentences_are_not_shown(calls):
    state = proposed_tls(calls)
    out, _ = turn("tls", state, "Explique les unités", reading(TLS_TASK, message="La longueur est fixée à 9 km."))
    assert "9 km" not in out["reply"] and "fixée" not in out["reply"]
    assert "Ce message n'a changé aucune valeur." in out["reply"]


@pytest.mark.parametrize("message", ["ok mais attends avant de calculer", "ok, but wait before computing"])
def test_a_request_to_wait_accepts_and_runs_nothing(calls, message):
    state = proposed_tls(calls)
    out, state = turn("tls", state, message, reading(TLS_TASK))
    assert out["decision"] == "clarify" and not calls
    assert not any(r["accepted"] for g in ("inputs", "experiment") for r in state[g].values()
                   if r.get("origin") == "default" and r.get("kind") == "default")


def test_pure_confirmation_runs_the_code(calls):
    accepted_tls(calls)


# ------------------------------------------------------------ unread or composite messages


def test_unread_composite_message_changes_nothing(calls):
    state = proposed_tls(calls)
    out, after = turn("tls", state, "oui, mais 45 jours au lieu de 7", None)
    assert after == state and out["decision"] == "clarify" and not calls


def test_change_with_yes_is_not_run_in_the_same_turn(calls):
    state = proposed_tls(calls)
    out, state = turn("tls", state, "oui, mais 45 jours au lieu de 7",
                      reading(TLS_TASK, {"field": "n_days", "value": 45, "unit": None, "origin": "provided",
                                         "evidence": "45 jours"}))
    assert out["decision"] == "clarify" and not calls
    assert state["experiment"]["n_days"]["value"] == 45
    assert "Noté d'après vos mots : **période simulée : 45 jours** (« 45 jours »)" in out["reply"]


def test_explanation_does_not_run(calls):
    state = accepted_tls(calls)
    out, _ = turn("tls", state, "Explique les unités, sans recalculer", reading(TLS_TASK, message="Les unités..."))
    assert out["decision"] == "clarify" and not calls


# ------------------------------------------------------------ strict translation


def test_invalid_change_blocks_and_keeps_the_old_value(calls):
    state = accepted_tls(calls)
    out, after = turn("tls", state, "La longueur est indéterminée",
                      reading(TLS_TASK, {"field": "length_m", "value": "indéterminée", "unit": None, "origin": "provided",
                                         "evidence": "La longueur est indéterminée"}))
    assert out["decision"] == "clarify" and not calls
    assert after["inputs"]["length_m"]["value"] == 2000
    assert "Je n'ai pas pu utiliser" in out["reply"]


@pytest.mark.parametrize("task", ["compare_schedules", "something else"])
def test_unknown_or_other_task_is_not_run(calls, task):
    state = json.loads(glue.api_fresh("lql", "fr"))
    out, _ = turn("lql", state, "Compare deux cures", reading(task))
    assert out["decision"] == "clarify" and not calls


def test_unsupported_task_is_refused(calls):
    state = json.loads(glue.api_fresh("lql", "fr"))
    out, _ = turn("lql", state, "Dois-je traiter mon patient M. Martin ?", reading("unsupported"))
    assert out["decision"] == "refuse" and not calls


def test_nested_course_field_is_rejected_not_flattened(calls):
    state = json.loads(glue.api_fresh("lql", "fr"))
    out, after = turn("lql", state, "deuxième cure de 4 Gy",
                      reading(LQL_TASK, {"field": "courses[1].dose_per_fraction", "value": 4, "unit": "Gy",
                                         "origin": "provided", "evidence": "4 Gy"}))
    assert "dose_per_fraction" not in after["inputs"] and not calls
    assert "plusieurs cures" in out["reply"]


def test_number_must_match_the_quoted_words(calls):
    state = json.loads(glue.api_fresh("tls", "fr"))
    out, after = turn("tls", state, "deux tubes",
                      reading(TLS_TASK, {"field": "n_tubes", "value": 7, "unit": None, "origin": "provided",
                                         "evidence": "deux tubes"}))
    assert after["inputs"]["n_tubes"]["value"] == 2 and after["inputs"]["n_tubes"]["origin"] == "default"
    assert "ne correspond pas" in out["reply"] and not calls


def test_number_words_weeks_and_kilometres_are_read_exactly(calls):
    state = json.loads(glue.api_fresh("tls", "en"))
    _, state = turn("tls", state, "two tubes over one week, a 3 km tunnel",
                    reading(TLS_TASK,
                            {"field": "n_tubes", "value": 2, "unit": None, "origin": "provided", "evidence": "two tubes"},
                            {"field": "n_days", "value": 7, "unit": None, "origin": "provided", "evidence": "one week"},
                            {"field": "length_m", "value": 3000, "unit": "m", "origin": "provided", "evidence": "3 km"}),
                    lang="en")
    assert state["inputs"]["n_tubes"]["value"] == 2 and state["inputs"]["n_tubes"]["origin"] == "provided"
    assert state["experiment"]["n_days"]["value"] == 7 and state["experiment"]["n_days"]["origin"] == "provided"
    assert state["inputs"]["length_m"]["value"] == 3000


def test_convention_value_comes_from_the_descriptor(calls):
    state = json.loads(glue.api_fresh("tls", "fr"))
    _, state = turn("tls", state, "beaucoup de trafic",
                    reading(TLS_TASK, {"field": "traffic_level", "value": 99, "unit": None, "origin": "convention",
                                       "level": "beaucoup", "evidence": "beaucoup de trafic"}))
    assert state["inputs"]["traffic_level"]["value"] == 1.5 and state["inputs"]["traffic_level"]["accepted"] is False


# ------------------------------------------------------------ outputs and limits


def test_not_computable_native_outputs_are_shown_as_such(tmp_path):
    (tmp_path / "manifest.json").write_text(json.dumps({"software": {}}), encoding="utf-8")
    (tmp_path / "indicators.csv").write_text("oar_total_valid,tumour_total_valid\nFalse,False\n", encoding="utf-8")
    none = {k: None for k in ("physical_dose_gy", "eqd_tumour_total", "eqd_oar_total", "tcp_percent", "ntcp_percent",
                              "bed_tumour", "overall_days_tumour")}
    out = glue.lql_results(tmp_path, none, "fr")
    assert out["kpis"][0] == "non calculable" and "non calculable" in out["analysis"]
    assert out["bars"] == [None, None, None]


def test_browser_limits_include_the_number_of_time_points():
    state = json.loads(glue.api_fresh("tls", "fr"))
    state["experiment"]["n_days"]["value"], state["experiment"]["n_runs"]["value"] = 60, 10
    state["experiment"].setdefault("freq_minutes", {})["value"] = 1
    assert glue.over_limit("tls", state)


def test_real_example_runs_with_the_pinned_codes():
    for model in ("tls", "lql"):
        out = json.loads(glue.api_example(model, "fr"))
        assert out["decision"] == "execute" and out["results"]["qualification"]["verification"]


def test_published_bundle_matches_the_sources():
    build = importlib.import_module("build_webapp")
    expected = build.entries()
    with zipfile.ZipFile(ROOT / "webapp" / "bundle.zip") as z:
        published = {n: z.read(n) for n in z.namelist()}
    assert published == expected
