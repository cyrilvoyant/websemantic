from pathlib import Path

import pytest

from websemantic import cli
from websemantic.conversation import explicit_consent
from websemantic.registry import load_descriptor
from websemantic.session import Session

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("prompt,evidence,expected", [
    ("J’accepte ces hypothèses, lance le calcul.", "J’accepte ces hypothèses", True),
    ("Prends le reste par défaut", "Prends le reste par défaut", True),
    ("J’accepte les hypothèses proposées, lance le calcul.", "J’accepte les hypothèses proposées, lance le calcul.", True),
    ("Je n’accepte pas ces hypothèses", "accepte ces hypothèses", False),
    ("J’accepte ces hypothèses ?", "J’accepte ces hypothèses", False),
    ("Propose des valeurs sans les accepter", "J’accepte ces hypothèses", False),
])
def test_consent_is_controlled_locally(prompt, evidence, expected):
    assert explicit_consent(prompt, evidence) is expected


def test_natural_proposal_inspection_explanation_and_acceptance(monkeypatch, tmp_path, capsys):
    lines = iter(["Propose les valeurs manquantes", "Montre le tableau avec unités", "Explique-moi la graine", "Propose cinq questions", "J’accepte ces hypothèses, lance le calcul.", "Quitte"])
    requests = []
    monkeypatch.setattr('builtins.input', lambda _: next(lines))
    monkeypatch.setattr(cli, 'load_private_key', lambda *args: None)

    def extract(text, descriptor, *args, **kwargs):
        requests.append(text)
        action = {"Propose les valeurs manquantes": "propose", "Montre le tableau avec unités": "details", "Explique-moi la graine": "explain", "Propose cinq questions": "suggest", "J’accepte ces hypothèses, lance le calcul.": "accept", "Quitte": "quit"}[text]
        return {"task": descriptor['tasks']['supported'][0], "updates": [], "message": "Voici les informations demandées.", "actions": [action], "parameter": "experiment.base_seed", "acceptance_evidence": "J’accepte ces hypothèses" if action == "accept" else ""}, {}

    monkeypatch.setattr(cli, 'extract', extract)
    assert cli.main(['chat', '--direct', '--workspace', str(ROOT), '--output-dir', str(tmp_path)]) == 0
    assert len(list(tmp_path.iterdir())) == 1
    text = capsys.readouterr().out
    assert 'Graine' in text and 'Dossier des résultats :' in text
    assert 'Outils :' not in text
    assert len(requests) == 6


def test_mixed_request_extracts_values_before_accepting_defaults(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, 'load_private_key', lambda *args: None)
    prompt = "Pour un tunnel de 2 km, propose les paramètres restants et j’accepte ces hypothèses."
    monkeypatch.setattr(cli, 'extract', lambda text, descriptor, *args, **kwargs: ({
        'task': descriptor['tasks']['supported'][0], 'updates': [{'field': 'inputs.length_m', 'value': '2', 'unit': 'km', 'evidence': '2 km'}],
        'actions': ['propose', 'accept'], 'acceptance_evidence': 'j’accepte ces hypothèses'}, {}))
    assert cli.main(['chat', '--direct', '--workspace', str(ROOT), '--output-dir', str(tmp_path), '--once', prompt]) == 0
    import json
    target = next(tmp_path.iterdir())
    scenario = json.loads((target/'manifest.json').read_text(encoding='utf-8'))['scenario']
    assert scenario['inputs']['length_m']['value'] == 2000
    assert scenario['inputs']['length_m']['origin'] == 'provided'


def test_even_wrong_interpreter_accept_action_cannot_authorize_a_negative(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, 'load_private_key', lambda *args: None)
    monkeypatch.setattr(cli, 'extract', lambda text, descriptor, *args, **kwargs: ({
        'task': descriptor['tasks']['supported'][0], 'updates': [], 'actions': ['propose', 'accept'],
        'acceptance_evidence': 'accepte ces hypothèses'}, {}))
    assert cli.main(['chat', '--direct', '--workspace', str(ROOT), '--output-dir', str(tmp_path), '--once', 'Je n’accepte ces hypothèses pas encore']) == 1
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('name', ['Graine', 'seed', 'base_seed', 'experiment.base_seed'])
def test_explanation_resolves_label_identifier_and_alias(name, capsys):
    cli.explain(Session(load_descriptor(ROOT, 'tls')), name)
    assert 'Graine' in capsys.readouterr().out
