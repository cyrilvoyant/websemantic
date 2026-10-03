from dataclasses import replace
from pathlib import Path

import pytest
import yaml
from rdflib import Graph

from websemantic.adapters.tls import run
from websemantic.cli import main
from websemantic.semantics import DEFINITIONS, describe
from websemantic.session import ClarificationNeeded, Session

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def session():
    return Session(yaml.safe_load((ROOT / 'descriptors/tls/descriptor.yaml').read_text(encoding='utf-8')))


def test_defaults_request_is_explicit_acceptance(session):
    assert session.local_intent('prends des valeurs moyennes')
    assert session.result().decision == 'execute'
    assert session.calls == 0


def test_unsupported_followup_does_not_destroy_task(session):
    previous = session.scenario.task
    with pytest.raises(ClarificationNeeded):
        session.apply('incompréhensible', {'task': 'unsupported', 'message': 'Précisez.', 'updates': []})
    assert session.scenario.task == previous
    session.local_intent('prends les valeurs par défaut')
    assert session.result().decision == 'execute'


def test_ajaccio_requires_acceptance_and_keeps_geometry(session):
    session.set_value('inputs.length_m', '2000')
    session.local_intent('altitude et autres comme Ajaccio')
    assert session.scenario.inputs['length_m'].value == 2000
    assert session.scenario.inputs['altitude_m'].value == 10
    assert not session.scenario.inputs['altitude_m'].accepted
    assert 'not a city mean' in session.scenario.inputs['altitude_m'].source
    assert session.result().decision == 'clarify'
    session.accept_profile()
    assert session.result().decision == 'execute'


def test_high_coefficients_proposal_is_not_silent_acceptance(session):
    session.local_intent('les plus couteux énergétiquement')
    assert session.scenario.inputs['lighting_type'].value == 'sodium fixed'
    assert session.result().decision == 'clarify'


def test_vocabulary_covers_every_parameter(session):
    assert set(DEFINITIONS) == set(session.descriptor['inputs']) | set(session.descriptor['experiment'])
    assert describe('aux_kw_per_km_tube')[1] == 'kW/(km·tube)'


def test_output_destination_and_rdf_without_thirty_run_limit(session, tmp_path):
    session.local_intent('prends les valeurs par défaut')
    session.scenario.experiment['n_runs'] = replace(session.scenario.experiment['n_runs'], value=31)
    target, _ = run(session.scenario, session.descriptor, ROOT, tmp_path)
    assert target.parent == tmp_path
    graph = Graph().parse(target / 'semantics.ttl')
    assert len(graph) > 200


def test_cli_short_commands_and_default_phrase(monkeypatch, capsys):
    lines = iter(['prends les valeurs par défaut', r'\d permet de vérifier', '/e altitude_m', r'\v', '/q'])
    monkeypatch.setattr('builtins.input', lambda _: next(lines))
    assert main(['chat', '--workspace', str(ROOT)]) == 0
    output = capsys.readouterr().out
    assert 'hypothèse validée' in output
    assert 'kW/(km·tube)' in output
    assert 'Altitude — unité : m' in output
    assert 'Sans plafond local' in output
    assert 'Commande inconnue' not in output


def test_spaced_length_is_not_truncated(session):
    session.apply('1 500 mètres', {'task': session.scenario.task, 'updates': [
        {'field': 'inputs.length_m', 'value': '1500', 'unit': 'unit:M', 'evidence': '1 500 mètres'}
    ]})
    assert session.scenario.inputs['length_m'].value == 1500


def test_explicit_dimensionless_number_uses_declared_unit(session):
    session.local_intent('prends les valeurs par défaut')
    session.apply('accident_sensitivity vaut 1', {'task': session.scenario.task, 'updates': [
        {'field': 'inputs.accident_sensitivity', 'value': '1', 'unit': '', 'evidence': 'accident_sensitivity vaut 1'}
    ]})
    assert session.scenario.inputs['accident_sensitivity'].unit == 'unit:UNITLESS'
    assert session.result().decision == 'execute'


def test_replay_user_conversation_and_open_results(monkeypatch, capsys, tmp_path):
    from websemantic import cli

    lines = iter(['prends les valeurs par défaut', 'fais un mix de tout stp puis une moyenne',
                  'altitude et autres comme Ajaccio', '/d permet de vérifier', '/v',
                  'les plus couteux energetiquement', '/v', '/r', '/q'])
    monkeypatch.setattr('builtins.input', lambda _: next(lines))
    opened = []
    monkeypatch.setattr(cli.os, 'startfile', lambda path: opened.append(path), raising=False)
    monkeypatch.setattr(cli, 'extract', lambda *args, **kwargs: pytest.fail('These requests should be local.'))
    assert main(['chat', '--workspace', str(ROOT), '--output-dir', str(tmp_path), '--open-results']) == 0
    text = capsys.readouterr().out
    assert 'Médiane' in text and 'Moyenne' in text
    assert 'unit:M' not in text
    assert 'Commande inconnue' not in text
    assert len(list(tmp_path.iterdir())) == 1
    if cli.os.name == 'nt':
        assert opened[0].parent == tmp_path
