from dataclasses import asdict
from pathlib import Path

import pytest

from websemantic import cli
from websemantic.registry import load_descriptor
from websemantic.session import Session
from websemantic.units import normalize, parse_number

ROOT = Path(__file__).resolve().parents[1]

BAD_ACCEPTANCES = [
    "Calcule la puissance moyenne d'un tunnel de 2 km.",
    "Je ne veux pas des valeurs par défaut ; calcule seulement si tout est fourni.",
    "Je n'accepte pas cette hypothèse.",
    "Pourquoi le profil par défaut utilise-t-il 1500 m ?",
    "Prends les valeurs par défaut pour un tunnel de 2 km.",
    "Accepte les valeurs par défaut ?",
    "Sans accepter les valeurs par défaut.",
    "Je ne veux pas faire un mix puis une moyenne.",
    "Pourquoi faire un mix puis une moyenne ?",
]


@pytest.mark.parametrize("prompt", BAD_ACCEPTANCES)
def test_mixed_negative_and_question_messages_do_not_accept_profile(prompt):
    session = Session(load_descriptor(ROOT, "tls"))
    session.propose_profile()
    before = asdict(session.scenario)
    assert session.local_intent(prompt) is None
    assert asdict(session.scenario) == before
    assert not session.run_requested
    assert all(not record.accepted for record in session.scenario.inputs.values())


@pytest.mark.parametrize("prompt", ["prends les valeurs par défaut", "Prends des valeurs moyennes.",
                                     "accepte les valeurs du profil", "calcule avec les valeurs par défaut"])
def test_standalone_acceptance_keeps_user_values(prompt):
    session = Session(load_descriptor(ROOT, "tls"))
    session.apply("2 km", {"task": session.scenario.task, "updates": [
        {"field": "inputs.length_m", "value": "2", "unit": "km", "evidence": "2 km"}]})
    before = session.scenario.inputs["length_m"]
    assert session.local_intent(prompt)
    assert session.scenario.inputs["length_m"] == before
    assert session.result().decision == "execute"


def test_mean_power_request_is_extracted_without_default_calculation(monkeypatch, tmp_path):
    prompt = BAD_ACCEPTANCES[0]
    requests = []
    monkeypatch.setattr(cli, "load_private_key", lambda *args: None)

    def extract(text, descriptor, *args, **kwargs):
        requests.append(text)
        return {"task": descriptor["tasks"]["supported"][0], "updates": [
            {"field": "inputs.length_m", "value": "2", "unit": "km", "evidence": "2 km"}], "message": "Précisez les autres paramètres."}, {}

    monkeypatch.setattr(cli, "extract", extract)
    def inspect_gate(session, *args):
        assert session.scenario.inputs["length_m"].value == 2000
        assert session.scenario.inputs["length_m"].origin == "provided"
        assert session.result().decision != "execute"

    monkeypatch.setattr(cli, "run_if_ready", inspect_gate)
    assert cli.main(["chat", "--direct", "--workspace", str(ROOT), "--output-dir", str(tmp_path), "--once", prompt]) == 0
    assert requests == [prompt]
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("prompt", BAD_ACCEPTANCES[1:4])
def test_negative_and_question_messages_reach_interpreter_without_local_acceptance(monkeypatch, tmp_path, prompt):
    calls = []
    monkeypatch.setattr(cli, "load_private_key", lambda *args: None)
    monkeypatch.setattr(cli, "extract", lambda text, descriptor, *args, **kwargs: (
        calls.append(text) or {"task": descriptor["tasks"]["supported"][0], "updates": [], "message": "Aucune hypothèse acceptée."}, {}))
    assert cli.main(["chat", "--direct", "--workspace", str(ROOT), "--output-dir", str(tmp_path), "--once", prompt]) == 0
    assert calls == [prompt] and not list(tmp_path.iterdir())


@pytest.mark.parametrize("text", ["1,500", "2,000", "-1,500", "12,345"])
def test_ambiguous_decimal_thousands_are_rejected(text):
    with pytest.raises(ValueError, match="ambigu"):
        parse_number(text, "float")
    spec = load_descriptor(ROOT, "tls")["inputs"]["length_m"]
    with pytest.raises(ValueError, match="ambigu"):
        normalize(1500, "m", text + " m", spec)


@pytest.mark.parametrize("text,expected", [("1,5", 1.5), ("0,015", 0.015), ("1.500", 1.5), ("1 500", 1500)])
def test_unambiguous_decimal_and_space_grouping(text, expected):
    assert parse_number(text, "float")[0] == expected


def test_model_evidence_divergence_is_traced_and_correct_conversion_is_not_flagged():
    spec = load_descriptor(ROOT, "tls")["inputs"]["length_m"]
    value, unit, source = normalize(1500, "unit:M", "2 km", spec)
    assert value == 2000 and unit == "unit:M"
    assert "Extraction divergence" in source and "1500" in source and "2 km" in source
    assert "Extraction divergence" not in normalize(2, "km", "2 km", spec)[2]


def test_ambiguous_evidence_does_not_change_existing_scenario():
    session = Session(load_descriptor(ROOT, "tls"))
    session.propose_profile()
    before = asdict(session.scenario)
    with pytest.raises(ValueError, match="ambigu"):
        session.apply("2,000 m", {"task": session.scenario.task, "updates": [
            {"field": "inputs.length_m", "value": "2000", "unit": "m", "evidence": "2,000 m"}]})
    assert asdict(session.scenario) == before
