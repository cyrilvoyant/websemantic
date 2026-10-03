"""Structural transfer fixtures, not validated LQL/pvlib integrations."""

import json
import sys
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
import yaml
from rdflib import Graph

from websemantic import cli, registry
from websemantic.geography import location
from websemantic.semantics import describe, export_semantics, vocabulary
from websemantic.session import Session


@pytest.fixture(params=[
    ('toy-dose', 'dose', 'unit:GRAY', 'Gy', 2.0, 'dose_result'),
    ('toy-solar', 'rated_power', 'unit:W', 'W', 500.0, 'power_result'),
])
def model(request):
    identity, name, canonical, symbol, default, indicator = request.param
    return {
        'software': {'name': identity, 'repository': 'https://example.org/' + identity, 'commit': 'test-fixture'},
        'nature': 'synthetic structural contract fixture',
        'inputs': {name: {'type': 'float', 'unit': canonical, 'label': name, 'display_unit': symbol,
                          'definition': 'Synthetic fixture parameter.', 'default': default, 'unit_aliases': [symbol]}},
        'experiment': {'repetitions': {'type': 'int', 'unit': 'unit:NUM', 'label': 'Répétitions',
                                      'display_unit': 'nombre', 'default': 2}},
        'tasks': {'supported': ['compute fixture']},
        'profile': {'source': 'Independent synthetic fixture, not a backend calibration.'},
        'runtime': {'adapter': 'websemantic.adapters.contract_fixture:run'},
        'presentation': {'namespace': 'websemantic.' + identity, 'short_name': identity,
                         'results': {'table': 'metrics.csv', 'indicators': [[indicator, 'Fixture result', symbol]]}},
        'semantics': {'intent_indicators': {'fixture_intent': indicator}},
    }


def test_descriptor_only_profile_units_labels_and_geography(model):
    session = Session(model)
    assert session.local_intent('prends les valeurs par défaut')
    assert session.result().decision == 'execute'
    field, spec = next(iter(model['inputs'].items()))
    value = str(spec['default'] * 2)
    session.apply(value, {'task': 'compute fixture', 'updates': [
        {'field': 'inputs.' + field, 'value': value, 'unit': spec['display_unit'], 'evidence': value}]})
    assert session.scenario.inputs[field].value == spec['default'] * 2
    assert session.scenario.inputs[field].unit == spec['unit']
    assert describe(field, model)[1] == spec['display_unit']
    assert len(vocabulary(model)) > 0
    assert location('Paris ou Ajaccio', model) is None
    assert len(cli.suggestions(session)) == 5
    assert 'length_m' not in session.scenario.inputs


def test_declared_adapter_dispatch_and_output_provenance(model, monkeypatch, tmp_path, capsys):
    calls = []
    module = ModuleType('websemantic.adapters.contract_fixture')

    def run(scenario, descriptor, workspace, output_root):
        calls.append(asdict(scenario))
        target = Path(output_root) / descriptor['software']['name']
        target.mkdir()
        indicator = descriptor['presentation']['results']['indicators'][0][0]
        parameter = next(iter(scenario.inputs.values()))
        value = parameter.value * scenario.experiment['repetitions'].value
        (target / 'metrics.csv').write_text(f'{indicator}\n{value}\n', encoding='utf-8')
        (target / 'manifest.json').write_text(json.dumps({'software': descriptor['software'], 'scenario': asdict(scenario)}), encoding='utf-8')
        export_semantics(scenario, {'tables': {'metrics': {'aggregation': 'Fixture only', 'columns': {
            indicator: {'meaning': 'Synthetic contract result', 'unit': descriptor['presentation']['results']['indicators'][0][2]}}}}}, target, descriptor)
        return target, {indicator: value}

    module.run = run
    monkeypatch.setitem(sys.modules, module.__name__, module)
    session = Session(model)
    session.run_requested = True
    args = SimpleNamespace(workspace=tmp_path, output_dir=tmp_path, open_results=False, llm='no-api', model=model['software']['name'])
    assert cli.run_if_ready(session, args, model) is None
    session.propose_profile()
    assert cli.run_if_ready(session, args, model) is None
    assert not calls
    session.accept_profile()
    target, _ = cli.run_if_ready(session, args, model)
    assert len(calls) == 1
    assert Graph().parse(target / 'semantics.ttl')
    assert json.loads((target / 'conversation.json').read_text())['environment'] == model['presentation']['namespace']
    assert 'Fixture result' in capsys.readouterr().out
    assert not session.run_requested


def test_catalogue_extension_loads_new_descriptor_without_core_edit(model, monkeypatch, tmp_path):
    folder = tmp_path / 'descriptors' / model['software']['name']
    folder.mkdir(parents=True)
    (folder / 'descriptor.yaml').write_text(yaml.safe_dump(model), encoding='utf-8')
    monkeypatch.setattr(registry, 'environments', lambda: [{'id': 'new-model', 'descriptor': model['software']['name']}])
    assert registry.load_descriptor(tmp_path, 'new-model') == model


def test_wrong_units_and_missing_defaults_still_block(model):
    descriptor = deepcopy(model)
    field = next(iter(descriptor['inputs']))
    descriptor['inputs'][field].pop('default')
    session = Session(descriptor)
    session.local_intent('prends les valeurs moyennes')
    assert session.result().decision == 'clarify'
    session.apply('3', {'task': session.scenario.task, 'updates': [
        {'field': 'inputs.' + field, 'value': '3', 'unit': 'unit:M', 'evidence': '3'}]})
    assert session.result().decision == 'clarify'
    assert any(issue.code == 'unit' for issue in session.result().issues)


def test_shared_python_modules_contain_no_tls_parameter_or_city_constants():
    root = Path(__file__).resolve().parents[1] / 'src/websemantic'
    for name in ('session.py', 'cli.py', 'gemini.py', 'geography.py', 'semantics.py', 'web_research.py', 'registry.py', 'units.py'):
        text = (root / name).read_text(encoding='utf-8')
        for forbidden in ('length_m', 'ventilation_type', 'tunnel_context', 'traffic_level', 'Ajaccio', 'Paris', 'kpis.csv', 'annualized_mwh'):
            assert forbidden not in text, (name, forbidden)


def test_adapter_reference_cannot_import_external_or_llm_selected_code():
    with pytest.raises(ValueError):
        registry.load_hook('os:system')


def test_negative_source_conversion_is_not_made_positive():
    from websemantic.units import normalize

    value, unit, _ = normalize(-2, 'km', '-2 km', {'unit': 'unit:M', 'evidence_conversion': {'units': {'km': 1000}}})
    assert value == -2000 and unit == 'unit:M'


def test_gemini_contract_is_generated_for_the_selected_descriptor(model, monkeypatch):
    from io import BytesIO

    from websemantic import gemini

    field, spec = next(iter(model['inputs'].items()))
    reply = {'task': 'compute fixture', 'message': 'Valeur fournie.', 'needs_web': False, 'updates': [
        {'field': 'inputs.' + field, 'value': '3', 'unit': spec['unit'], 'evidence': '3'}]}
    captured = []

    def respond(request, **kwargs):
        captured.append(json.loads(request.data))
        return BytesIO(json.dumps({'output_text': json.dumps(reply)}).encode())

    monkeypatch.setattr(gemini, 'api_key', lambda: 'fixture-key-not-a-credential')
    monkeypatch.setattr(gemini.urllib.request, 'urlopen', respond)
    parsed, _ = gemini.extract('3', model, [], model='fixture-model')
    schema = captured[0]['response_format']['schema']
    declared = schema['properties']['updates']['items']['properties']['field']['enum']
    assert declared == ['inputs.' + field, 'experiment.repetitions']
    assert parsed == reply
    assert 'length_m' not in captured[0]['input']
