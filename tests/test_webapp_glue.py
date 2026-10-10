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


def test_a_tumour_site_read_as_an_organ_is_moved_by_the_library_lists(calls):
    """Browser retest: 'Prostate, rectum comme organe à risque' read as organ=Prostate then organ=Rectum."""
    state = json.loads(glue.api_fresh("lql", "fr"))
    msg = "Prostate, rectum comme organe à risque, 20 séances de 3 Gy, sans interruption."
    out, after = turn("lql", state, msg, reading(
        LQL_TASK, {"field": "organ", "value": "Prostate", "origin": "provided", "evidence": "Prostate"},
        {"field": "organ", "value": "Rectum", "origin": "provided", "evidence": "rectum"},
        {"field": "gap_days", "value": 0, "unit": "unit:DAY", "origin": "provided", "evidence": "sans interruption"}))
    assert after["inputs"]["tumour_site"]["value"] == "Prostate" and after["inputs"]["organ"]["value"] == "Rectum"
    assert after["inputs"]["gap_days"]["value"] == 0 and not calls


def test_two_readings_for_one_other_field_use_neither(calls):
    state = json.loads(glue.api_fresh("tls", "fr"))
    out, after = turn("tls", state, "un tunnel de 2 km ou 3 km", reading(
        TLS_TASK, {"field": "length_m", "value": 2000, "unit": "m", "origin": "provided", "evidence": "2 km"},
        {"field": "length_m", "value": 3000, "unit": "m", "origin": "provided", "evidence": "3 km"}))
    assert after["inputs"]["length_m"]["origin"] == "default" and "deux lectures différentes" in out["reply"]


def test_reading_context_lists_the_library_categories():
    lql = json.loads((ROOT / "webapp" / "llm" / "lql.json").read_text(encoding="utf-8"))
    cats = {p["field"]: p.get("categories") or [] for p in lql["params"]}
    assert "Rectum" in cats["organ"] and "Prostate" in cats["tumour_site"] and "Prostate" not in cats["organ"]


def test_the_model_sentences_are_not_shown(calls):
    state = proposed_tls(calls)
    out, _ = turn("tls", state, "Explique les unités", reading(TLS_TASK, message="La longueur est fixée à 9 km."))
    assert "9 km" not in out["reply"] and "fixée" not in out["reply"]
    assert "Ce message n'a changé aucune valeur." in out["reply"]


def test_the_model_questions_are_not_shown(calls):
    """Online test by Cyril: the model asked for the tumour site while the deterministic list asked for the organ."""
    state = json.loads(glue.api_fresh("lql", "fr"))
    parsed = dict(reading(LQL_TASK), questions=["Quel est le site tumoral ?"])
    out, _ = turn("lql", state, "tous les organes à risque", parsed)
    assert "site tumoral ?" not in out["reply"] and "Il manque encore" in out["reply"]


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
    assert "Noté d'après vos mots : **période simulée : 7 jours → 45 jours** (« 45 jours »)" in out["reply"]


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
    assert out["kpis"][0] == "non calculable" and "non calculable" in out["headline"]
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


@pytest.mark.parametrize("model", ["tls", "lql"])
def test_the_rdf_graph_of_each_result_is_downloadable(model):
    """The graph written by export_semantics (ontology terms, units, provenance) is offered with the result."""
    out = json.loads(glue.api_example(model, "fr"))
    ttl = out["results"]["files"]["semantics.ttl"]
    assert "@prefix wsem: <https://w3id.org/websemantic/ns#>" in ttl and "prov:" in ttl


@pytest.mark.parametrize("words,expected", [("sur un an", 365), ("une année", 365), ("over one year", 365),
                                            ("2 ans", 730), ("deux semaines", 14)])
def test_years_and_weeks_are_converted_exactly(words, expected):
    assert expected in glue.evidence_numbers(words)


def test_the_english_article_an_is_not_a_year():
    assert 3650 not in glue.evidence_numbers("an interruption of 10 days")


def test_one_year_is_allowed_and_more_is_refused_before_running(calls):
    state = accepted_tls(calls)
    state["experiment"]["n_days"]["value"] = 365
    state["experiment"]["n_runs"]["value"] = 10
    state["experiment"]["freq_minutes"] = dict(state["experiment"].get("freq_minutes", {}), value=15)
    assert not glue.over_limit("tls", state)
    state["experiment"]["n_days"]["value"] = 400
    assert glue.over_limit("tls", state)


# ------------------------------------------------------------ Cyril's online test: "200 m higher", then "that means 1200 m"


def altitude_1000(calls):
    state = accepted_tls(calls)
    out, state = turn("tls", state, "change l'altitude à 1000m",
                      reading(TLS_TASK, {"field": "altitude_m", "value": 1000, "unit": "m", "origin": "provided",
                                         "evidence": "change l'altitude à 1000m"}))
    out, state = turn("tls", state, "oui")
    assert state["inputs"]["altitude_m"]["value"] == 1000 and calls == ["tls"]
    calls.clear()
    return state


def test_an_exact_relative_change_is_applied_and_shown(calls):
    state = altitude_1000(calls)
    out, state = turn("tls", state, "une altitude plus importante de 200m",
                      reading(TLS_TASK, {"field": "altitude_m", "value": 1200, "unit": "m", "origin": "provided",
                                         "evidence": "plus importante de 200m"}))
    assert state["inputs"]["altitude_m"]["value"] == 1200 and not calls
    assert "1 000 m → 1 200 m" in out["reply"].replace(glue.NBSP, " ") and "+ 200 m" in out["reply"]


def test_a_failed_request_blocks_the_confirmation(calls):
    state = altitude_1000(calls)
    out, state = turn("tls", state, "une altitude plus importante de 200m",
                      reading(TLS_TASK, {"field": "altitude_m", "value": 1500, "unit": "m", "origin": "provided",
                                         "evidence": "plus importante de 200m"}))  # not 1000 + 200: refused
    assert state["inputs"]["altitude_m"]["value"] == 1000 and state["unresolved"] == ["altitude_m"]
    assert "Répondez **oui** pour lancer" not in out["reply"] and "Reste en suspens" in out["reply"]
    out, state = turn("tls", state, "oui")
    assert not calls and out["decision"] == "clarify"  # the old altitude is not computed silently
    out, state = turn("tls", state, "garder", reading(TLS_TASK))
    assert state["unresolved"] == [] and "garde sa valeur actuelle" in out["reply"]
    out, state = turn("tls", state, "oui")
    assert calls == ["tls"]


def test_an_unnamed_change_of_a_stated_value_is_flagged(calls):
    state = altitude_1000(calls)
    out, state = turn("tls", state, "ça veut dire 1200 metre",
                      reading(TLS_TASK, {"field": "length_m", "value": 1200, "unit": "m", "origin": "provided",
                                         "evidence": "1200 metre"}))
    text = out["reply"].replace(glue.NBSP, " ")
    assert "2 000 m → 1 200 m" in text and "non nommé" in text


def test_the_reading_context_carries_the_unresolved_parameter(calls):
    state = altitude_1000(calls)
    state["unresolved"] = ["altitude_m"]
    state["request"] += "\nune altitude plus importante de 200m"
    summary = json.loads(glue.api_summary(json.dumps(state)))
    assert summary["unresolved"] == ["altitude_m"] and summary["previous_message"].endswith("200m")


# ------------------------------------------------------------ conventions come only from the descriptor (contract, rule 3)


def test_english_expressions_are_declared_in_the_descriptor(calls):
    state = json.loads(glue.api_fresh("tls", "en"))
    out, state = turn("tls", state, "A long tunnel with a lot of traffic",
                      reading(TLS_TASK, {"field": "length_m", "origin": "convention", "level": "très élevé",
                                         "evidence": "long tunnel"},
                              {"field": "traffic_level", "origin": "convention", "level": "énormément",
                               "evidence": "a lot of traffic"}), lang="en")
    assert state["inputs"]["length_m"]["value"] == 9000 and state["inputs"]["traffic_level"]["value"] == 1.5


def test_words_outside_the_tables_are_asked_not_given_a_level(calls):
    state = json.loads(glue.api_fresh("tls", "en"))
    out, state = turn("tls", state, "A rather lengthy tunnel",
                      reading(TLS_TASK, {"field": "length_m", "origin": "convention", "level": "élevé",
                                         "evidence": "rather lengthy tunnel"}), lang="en")
    assert state["inputs"]["length_m"]["origin"] == "default" and state["inputs"]["length_m"]["value"] == 1500
    assert "no declared convention" in out["reply"] and state["unresolved"] == ["length_m"]


def test_a_declared_expression_claimed_as_a_number_gets_the_descriptor_value(calls):
    state = json.loads(glue.api_fresh("tls", "en"))
    out, state = turn("tls", state, "frequent accidents",
                      reading(TLS_TASK, {"field": "accident_probability_per_day", "value": 0.15, "origin": "provided",
                                         "evidence": "frequent accidents"}), lang="en")
    rec = state["inputs"]["accident_probability_per_day"]
    assert rec["kind"] == "convention" and rec["accepted"] is False and rec["value"] != 0.15


def test_the_quote_is_stored_with_the_visitors_own_characters(calls):
    state = json.loads(glue.api_fresh("lql", "fr"))
    out, state = turn("lql", state, "Dose équivalente pour la prostate",
                      reading(LQL_TASK, {"field": "tumour_site", "value": "Prostate", "origin": "provided",
                                         "evidence": "Prostate"}))
    assert state["inputs"]["tumour_site"]["evidence"] == "prostate"


# ------------------------------------------------------------ Cyril's online test: a second example typed into the first case


def test_a_restated_value_is_not_flagged_and_a_new_case_is_suggested(calls):
    state = json.loads(glue.api_fresh("lql", "fr"))
    msg1 = "Glioblastome, chiasma optique comme organe à risque, 30 séances de 2 Gy."
    out, state = turn("lql", state, msg1, reading(
        LQL_TASK, {"field": "tumour_site", "value": "Glioblastoma (LQ-L)", "origin": "provided", "evidence": "Glioblastome"},
        {"field": "organ", "value": "Optic chiasm", "origin": "provided", "evidence": "chiasma optique"},
        {"field": "n_fractions", "value": 30, "origin": "provided", "evidence": "30 séances"},
        {"field": "dose_per_fraction", "value": 2, "unit": "unit:GRAY", "origin": "provided", "evidence": "2 Gy"}))
    msg2 = "Tumeur du larynx, parotide comme organe à risque, 35 séances de 2 Gy."
    out, state = turn("lql", state, msg2, reading(
        LQL_TASK, {"field": "tumour_site", "value": "Larynx", "origin": "provided", "evidence": "Tumeur du larynx"},
        {"field": "organ", "value": "Parotid", "origin": "provided", "evidence": "parotide"},
        {"field": "n_fractions", "value": 35, "origin": "provided", "evidence": "35 séances"},
        {"field": "dose_per_fraction", "value": 2, "unit": "unit:GRAY", "origin": "provided", "evidence": "2 Gy"}))
    reply = out["reply"]
    assert "dose par séance" not in reply  # restated unchanged: neither listed nor flagged
    assert "non nommé" not in reply  # "tumeur", "organe", "séances" name the changed fields
    assert "Glioblastoma (LQ-L) → Larynx" in reply and "Nouvelle conversation" in reply and not calls


def test_a_refusal_during_a_case_says_the_case_is_unchanged(calls):
    state = proposed_tls(calls)
    out, after = turn("tls", state, "pas pareil !", reading("unsupported"))
    assert out["decision"] == "refuse" and "Le cas en cours est inchangé" in out["reply"]
    assert after["inputs"] == state["inputs"] and not calls


# ------------------------------------------------------------ LQL workbench through the conversation (real LQL-Equiv runs)


def lql_case(message, *values, lang="fr", state=None):
    state = state or json.loads(glue.api_fresh("lql", lang))
    out, state = turn("lql", state, message, reading(LQL_TASK, *values), lang=lang)
    return out, state


SITE = {"field": "tumour_site", "value": "Prostate", "origin": "provided", "evidence": "prostate"}
RECTUM = {"field": "organ", "value": "Rectum", "origin": "provided", "evidence": "rectum"}
BOWEL = {"field": "organ", "value": "Small bowel", "origin": "provided", "evidence": "grêle"}


def yes(state, lang="fr"):
    return turn("lql", state, "oui" if lang == "fr" else "yes", lang=lang)


def test_several_organs_give_one_row_each():
    out, state = lql_case("20 séances de 3 Gy pour la prostate, rectum et grêle comme organes à risque", SITE, RECTUM, BOWEL,
                          {"field": "dose_per_fraction", "value": 3, "origin": "provided", "evidence": "3 Gy"},
                          {"field": "n_fractions", "value": 20, "origin": "provided", "evidence": "20 séances"})
    assert state["organs"] == ["Rectum", "Small bowel"]
    out, state = yes(state)
    r = out["results"]
    assert out["decision"] == "execute" and r["kind"] == "lql_table"
    assert [row[0] for row in r["table"]["rows"]][1:] == ["Rectum", "Small bowel"] and "Réponse" in out["reply"]


def test_two_schedules_are_compared_from_the_words():
    out, state = lql_case("Compare 20 × 3 Gy et 39 séances de 2 Gy avec une interruption de 10 jours, prostate, rectum",
                          SITE, RECTUM)
    assert state["lql"]["mode"] == "compare" and len(state["lql"]["schedules"]) == 2
    assert state["lql"]["schedules"][1]["gap_days"] == 10 and state["lql"]["schedules"][0]["gap_days"] == 0
    out, state = yes(state)
    assert out["results"]["table"]["head"][1:] == ["20 × 3 Gy", "39 × 2 Gy, arrêt de 10 jours"]


def test_resumption_asks_when_the_sessions_given_are_ambiguous():
    msg = ("prostate 35×2gy, 5 jours d'arrêt, on veut garder le même nombre de séances, nous sommes à la 15ème séance, "
           "rectum comme organe à risque")
    out, state = lql_case(msg, SITE, RECTUM)
    assert state["lql"]["mode"] == "resume" and state["lql"]["ambiguous_done"] == 15
    out, state = yes(state)
    assert "14 séances déjà faites" in out["reply"] and out["decision"] == "clarify"
    out, state = turn("lql", state, "14", reading(LQL_TASK))
    out, state = yes(state)
    r = out["results"]
    assert out["decision"] == "execute" and state["lql"]["remaining"] == 21
    assert "21 séances restantes" in out["reply"] and "dose maximale" in out["reply"]


def test_maximum_dose_reports_the_limiting_organ():
    msg = "dose maximale en 20 séances sans dépasser l'équivalent de 39 × 2 Gy pour la prostate, rectum et vessie"
    out, state = lql_case(msg, SITE, RECTUM, {"field": "organ", "value": "Bladder", "origin": "provided", "evidence": "vessie"})
    assert state["lql"]["mode"] == "maximum" and state["lql"]["target"] == 20
    out, state = yes(state)
    assert out["decision"] == "execute" and "limitée par" in out["reply"]


def test_all_organs_come_from_the_ontology_and_are_confirmed():
    out, state = lql_case("20 séances de 3 Gy pour la prostate, tous les organes à risque", SITE,
                          {"field": "dose_per_fraction", "value": 3, "origin": "provided", "evidence": "3 Gy"},
                          {"field": "n_fractions", "value": 20, "origin": "provided", "evidence": "20 séances"})
    assert "Pelvis" in out["reply"] and "Rectum" in out["reply"] and out["decision"] == "clarify"
    assert state["inputs"]["organ"]["accepted"] is False and len(state["organs"]) == 7
    out, state = yes(state)
    assert out["decision"] == "execute" and len(out["results"]["table"]["rows"]) == 8


def test_an_organ_of_another_group_is_dropped_when_the_tumour_changes():
    out, state = lql_case("tumeur du larynx, parotide", {"field": "tumour_site", "value": "Larynx", "origin": "provided",
                                                         "evidence": "tumeur du larynx"},
                          {"field": "organ", "value": "Parotid", "origin": "provided", "evidence": "parotide"})
    out, state = turn("lql", state, "en fait une tumeur de la prostate", reading(
        LQL_TASK, {"field": "tumour_site", "value": "Prostate", "origin": "provided", "evidence": "tumeur de la prostate"}))
    assert "organ" not in state["inputs"] and "Parotid" in out["reply"] and "Pelvis" in out["reply"]


def test_months_are_a_declared_conversion_to_accept(calls):
    state = accepted_tls(calls)
    out, state = turn("tls", state, "non prends 6 mois", reading(
        TLS_TASK, {"field": "n_days", "value": 180, "unit": "unit:DAY", "origin": "provided", "evidence": "6 mois"}))
    rec = state["experiment"]["n_days"]
    assert rec["value"] == 182 and rec["accepted"] is False and "365/12" in rec["source"] and not calls
    out, state = turn("tls", state, "oui")
    assert calls == ["tls"]


def test_minimum_organ_dose_for_the_same_tumour_effect():
    msg = "dose minimale aux organes pour le même effet tumoral que 39 × 2 Gy, prostate, rectum et grêle"
    out, state = lql_case(msg, SITE, RECTUM, BOWEL)
    assert state["lql"]["mode"] == "minimum"
    out, state = yes(state)
    assert out["decision"] == "execute" and "le moins exposés" in out["reply"]
    assert out["results"]["chart"]["unit"] == "%"


def test_the_ontology_names_catch_an_organ_the_model_missed():
    out, state = lql_case("20 séances de 3 Gy pour la prostate, vessie comme organe à risque",
                          {"field": "dose_per_fraction", "value": 3, "origin": "provided", "evidence": "3 Gy"},
                          {"field": "n_fractions", "value": 20, "origin": "provided", "evidence": "20 séances"})
    assert state["inputs"]["tumour_site"]["value"] == "Prostate" and state["inputs"]["organ"]["value"] == "Bladder"
    assert state["inputs"]["organ"]["evidence"] == "vessie"


# ------------------------------------------------------------ successive courses ("2 runs"), Cyril's online test


def test_two_runs_with_a_break_are_cumulated():
    msg = "2 runs avec 15 jours d'arrêt : 20 × 3,5 Gy puis 1 × 1,8 Gy, prostate, rectum et vessie"
    out, state = lql_case(msg, SITE, RECTUM, {"field": "organ", "value": "Bladder", "origin": "provided", "evidence": "vessie"})
    L = state["lql"]
    assert L["mode"] == "sequence" and [c["gap_days"] for c in L["courses"]] == [0.0, 15.0]
    out, state = yes(state)
    r = out["results"]
    assert out["decision"] == "execute" and "EQD2 cumulée" in out["reply"] and r["table"]["head"][-1] == "total"


def test_three_courses_and_the_breaks_between_them():
    msg = "prostate, rectum : 20 × 3 Gy, puis 10 jours d'arrêt, puis 5 × 2 Gy, puis 7 jours d'arrêt, puis 2 × 4 Gy"
    out, state = lql_case(msg, SITE, RECTUM)
    assert [c["gap_days"] for c in state["lql"]["courses"]] == [0.0, 10.0, 7.0]
    out, state = yes(state)
    assert out["decision"] == "execute" and len(out["results"]["table"]["head"]) == 5


def test_an_unrecognised_schedule_is_asked_not_guessed():
    out, state = lql_case("20c3.5 puis 1×1.8Gy, prostate, rectum", SITE, RECTUM)
    assert "20c3.5" in out["reply"] and state["unresolved"] == ["schedule"]
    out, state = yes(state)
    assert out["decision"] == "clarify" and "schéma" in out["reply"] and not out.get("results")
    out, state = turn("lql", state, "20 × 3,5 Gy puis 1 × 1,8 Gy", reading(LQL_TASK))
    assert state["unresolved"] == [] and state["lql"]["mode"] == "sequence"


def test_two_schedules_without_a_word_ask_whether_to_chain_or_compare():
    out, state = lql_case("20 × 3 Gy et 39 × 2 Gy, prostate, rectum", SITE, RECTUM)
    assert state["lql"]["mode"] == "choose"
    out, state = yes(state)
    assert "l'un après l'autre" in out["reply"]
    out, state = turn("lql", state, "l'un après l'autre", reading(LQL_TASK))
    assert state["lql"]["mode"] == "sequence" and len(state["lql"]["courses"]) == 2
