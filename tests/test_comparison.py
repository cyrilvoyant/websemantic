import json
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path

import jsonschema
import pandas as pd
import pytest
from rdflib import Graph, URIRef

from websemantic import cli
from websemantic.comparison import run, validation
from websemantic.registry import load_descriptor
from websemantic.semantics import PROV, WS
from websemantic.session import ClarificationNeeded, Session

ROOT = Path(__file__).resolve().parents[1]
DESCRIPTOR = load_descriptor(ROOT, 'tls')


def update(field, value, evidence, unit=''):
    return {'field':field, 'value':str(value), 'evidence':evidence, 'unit':unit}


def start(state):
    request = 'Deux tunnels de 5 km : scénario 1, 3 voies par tube et LED fixed ; scénario 2, 2 voies par tube et sodium fixed.'
    state.apply(request, {'task': DESCRIPTOR['tasks']['supported'][1], 'comparison': True,
        'updates': [update('inputs.length_m',5,'5 km','km')],
        'scenario_updates': [
            {'scenario':'scenario_1','updates': [update('inputs.n_lanes_per_tube',3,'3 voies par tube'),update('inputs.lighting_type','LED fixed','LED fixed')], 'questions': []},
            {'scenario':'scenario_2','updates': [update('inputs.n_lanes_per_tube',2,'2 voies par tube'),update('inputs.lighting_type','sodium fixed','sodium fixed')], 'questions': []}]})
    return state


def ready():
    state = start(Session(deepcopy(DESCRIPTOR)))
    state.propose_profile()
    state.set_value('experiment.n_days', '1')
    state.set_value('experiment.n_runs', '2')
    state.accept_profile()
    return state


def test_scenario_parameters_are_separate_and_defaults_require_acceptance():
    state = start(Session(deepcopy(DESCRIPTOR)))
    assert state.scenarios['scenario_1'].scenario.inputs['n_lanes_per_tube'].value == 3
    assert state.scenarios['scenario_2'].scenario.inputs['n_lanes_per_tube'].value == 2
    state.propose_profile()
    assert state.result().decision == 'clarify'
    assert not state.scenarios['scenario_1'].scenario.inputs['altitude_m'].accepted
    assert state.scenarios['scenario_1'].scenario.experiment['base_seed'].value == 42


def test_bad_second_scenario_is_atomic_and_more_than_two_is_rejected():
    state = ready()
    before = deepcopy({label: child.scenario for label,child in state.scenarios.items()})
    with pytest.raises(ValueError):
        state.apply('3 et impossible', {'task': state.scenario.task, 'updates': [], 'scenario_updates': [
            {'scenario':'scenario_1','updates':[update('inputs.n_lanes_per_tube',3,'3')], 'questions':[]},
            {'scenario':'scenario_2','updates':[update('inputs.n_lanes_per_tube','impossible','impossible')], 'questions':[]}]})
    assert {label:child.scenario for label,child in state.scenarios.items()} == before
    with pytest.raises(ClarificationNeeded):
        state.apply('trois scénarios', {'task': state.scenario.task,'updates':[], 'scenario_updates':[{'scenario':str(i)} for i in range(3)]})


@pytest.mark.parametrize('field,value', [('start_date','"2026-01-01"'),('n_days','2'),('freq_minutes','15'),('n_runs','3'),('base_seed','43')])
def test_controls_must_match_before_any_execution(tmp_path, field, value):
    state = ready()
    state.set_value('scenario_2.experiment.'+field, value)
    assert any(issue.code=='comparison_control' for issue in state.result().issues)
    with pytest.raises(ValueError):
        run(state.scenarios, state.descriptor, ROOT, tmp_path)
    assert not list(tmp_path.iterdir())


def test_explicit_equality_carries_provenance_and_no_implicit_length_copy():
    state = Session(deepcopy(DESCRIPTOR))
    state.apply('Scénario 1 : 5 km', {'task':state.scenario.task,'comparison':True,'updates':[], 'scenario_updates':[
        {'scenario':'scenario_1','updates':[update('inputs.length_m',5,'5 km','km')], 'questions':[]}]})
    assert 'length_m' not in state.scenarios['scenario_2'].scenario.inputs
    state.apply('Pour le scénario 2, la même longueur', {'task':state.scenario.task,'updates':[], 'scenario_updates':[],
        'shared_from':[{'field':'inputs.length_m','source':'scenario_1','target':'scenario_2','evidence':'la même longueur'}]})
    record=state.scenarios['scenario_2'].scenario.inputs['length_m']
    assert record.value==5000 and record.accepted and 'scenario_1' in record.source


def test_ambiguous_equipment_still_blocks_both_runs():
    state=ready()
    state.scenarios['scenario_2'].add_questions([{'question':'Quel éclairage ancien ?', 'fields':['inputs.lighting_type'],'blocking':True}])
    state.refresh_comparison()
    assert state.local_intent('Prends les valeurs par défaut')
    assert state.result().decision=='clarify'
    assert validation(state.scenarios,state.descriptor).decision=='clarify'


def test_native_comparison_preserves_each_csv_and_qualified_scenario_column(tmp_path, capsys):
    state=ready()
    target, report=run(state.scenarios,state.descriptor,ROOT,tmp_path)
    manifest=json.loads((target/'manifest.json').read_text(encoding='utf-8'))
    assert manifest['status']=='complete'
    for table in manifest['outputs']:
        combined=pd.read_csv(target/(table+'.csv'))
        assert set(combined.scenario)=={'scenario_1','scenario_2'}
        assert manifest['output_qualification']['tables'][table]['columns']['scenario']['unit'] is None
        for label,path in manifest['scenario_runs'].items():
            original=pd.read_csv(Path(path)/(table+'.csv'))
            actual=combined[combined.scenario==label].drop(columns='scenario').reset_index(drop=True)
            pd.testing.assert_frame_equal(original,actual)
    kpis=pd.read_csv(target/'kpis.csv')
    for label in ('scenario_1','scenario_2'):
        assert list(kpis[kpis.scenario==label].seed)==[42,43]
        assert list(kpis[kpis.scenario==label].base_seed)==[42,42]
    difference=report['differences']['total_mwh']
    assert difference['difference_1_minus_2']==pytest.approx(difference['scenario_1']-difference['scenario_2'])
    for indicator, difference in report['differences'].items():
        for label in ('scenario_1', 'scenario_2'):
            assert difference[label] == pytest.approx(kpis[kpis.scenario == label][indicator].median())
    graph = Graph().parse(target/'semantics.ttl',format='turtle')
    output = URIRef((target/'kpis.csv').resolve().as_uri())
    assert len(list(graph.objects(output, PROV.wasDerivedFrom))) == 2
    for child in graph.objects(output, PROV.wasDerivedFrom):
        assert list(graph.objects(child, PROV.wasGeneratedBy))
        assert list(graph.objects(child, WS.scenarioIdentifier))
    schema=json.loads((ROOT/'ontology/tls-comparison.schema.json').read_text(encoding='utf-8'))
    jsonschema.validate(json.loads(json.dumps({label:asdict(child.scenario) for label,child in state.scenarios.items()})),schema)
    cli.results_table(state,target,report)
    assert 'Scénario 1' in capsys.readouterr().out


def test_terminal_comparison_runs_both_after_global_acceptance(monkeypatch,tmp_path,capsys):
    messages=iter(['Compare mes deux scénarios sur 1 jour avec 1 réalisation','Prends le reste par défaut','/d','/q'])
    monkeypatch.setattr('builtins.input',lambda _:next(messages))
    monkeypatch.setattr(cli,'load_private_key',lambda *args:None)
    def extraction(request,descriptor,*args,**kwargs):
        return {'task':descriptor['tasks']['supported'][1],'comparison':True,'message':'Deux scénarios distincts.',
            'updates':[update('experiment.n_days',1,'1 jour','unit:DAY'),update('experiment.n_runs',1,'1 réalisation')],
            'scenario_updates':[], 'questions':[],'actions':[]},{}
    monkeypatch.setattr(cli,'extract',extraction)
    assert cli.main(['chat','--direct','--workspace',str(ROOT),'--output-dir',str(tmp_path)])==0
    assert len(list(tmp_path.glob('*/comparison.json')))==1
    text=capsys.readouterr().out
    assert 'Scénario 1' in text and 'Scénario 2' in text and 'Dossier des résultats' in text


def test_second_execution_failure_is_marked_incomplete(monkeypatch,tmp_path):
    from websemantic import registry

    original=registry.execute
    calls=[]
    def execution(*args,**kwargs):
        calls.append(1)
        if len(calls)==2:
            raise ValueError('Fixture: second adapter failed')
        return original(*args,**kwargs)
    monkeypatch.setattr(registry,'execute',execution)
    state=ready()
    with pytest.raises(ValueError):
        run(state.scenarios,state.descriptor,ROOT,tmp_path)
    target=next(tmp_path.iterdir())
    assert (target/'INCOMPLETE.txt').is_file()
    assert not (target/'manifest.json').exists()


def test_same_scenario_gives_zero_differences(tmp_path):
    state=ready()
    state.set_value('scenario_2.inputs.n_lanes_per_tube','3')
    state.set_value('scenario_2.inputs.lighting_type','"LED fixed"')
    _,report=run(state.scenarios,state.descriptor,ROOT,tmp_path)
    assert all(item['difference_1_minus_2']==0 and item['relative_percent_vs_2']==0 for item in report['differences'].values())


def test_explicit_equality_can_revise_a_previous_value_without_touching_source():
    state=ready()
    state.set_value('scenario_2.inputs.length_m','3000')
    source=state.scenarios['scenario_1'].scenario.inputs['length_m']
    state.apply('Pour le scénario 2, prends la même longueur', {'task':state.scenario.task,'updates':[],
        'shared_from':[{'field':'inputs.length_m','source':'scenario_1','target':'scenario_2','evidence':'la même longueur'}]})
    assert state.scenarios['scenario_2'].scenario.inputs['length_m'].value==5000
    assert state.scenarios['scenario_1'].scenario.inputs['length_m']==source


def test_a_question_is_attached_only_to_its_scenario():
    state=ready()
    state.apply('L’éclairage du scénario 2 est ancien', {'task':state.scenario.task,'updates':[],
        'questions':[{'scenario':'scenario_2','question':'Quel type d’éclairage ?',
                      'fields':['inputs.lighting_type'],'blocking':True}]})
    assert not state.scenarios['scenario_1'].questions
    assert state.scenarios['scenario_2'].questions
    assert state.pending_clarification


def test_external_comparison_cannot_ignore_a_third_scenario(tmp_path):
    state=ready()
    state.scenarios['scenario_3']=deepcopy(state.scenarios['scenario_2'])
    with pytest.raises(ValueError):
        run(state.scenarios,state.descriptor,ROOT,tmp_path)
    assert not list(tmp_path.iterdir())


def test_comparison_reads_rdf_as_data_without_url_loader(tmp_path, monkeypatch):
    import rdflib.parser

    def forbidden_url(*args, **kwargs):
        raise AssertionError("RDF must be read through the filesystem, not URL loading")

    monkeypatch.setattr(rdflib.parser, "_urlopen", forbidden_url)
    state = ready()
    target, _ = run(state.scenarios, DESCRIPTOR, ROOT, tmp_path)
    assert json.loads((target / "manifest.json").read_text())["status"] == "complete"
    assert (target / "semantics.ttl").is_file()
