import json
from copy import deepcopy
from pathlib import Path

from rdflib import Graph, Literal
from rdflib.namespace import RDF, SKOS

from websemantic.adapters.tls import run
from websemantic.registry import load_descriptor
from websemantic.semantics import PROV, WS, concept, vocabulary
from websemantic.session import Session

ROOT = Path(__file__).resolve().parents[1]


def test_concepts_are_model_scoped_and_parameter_meanings_are_complete():
    descriptor = load_descriptor(ROOT, 'tls')
    other = deepcopy(descriptor)
    other['semantics']['namespace'] = 'another-model'
    other['inputs']['length_m']['definition'] = 'Independent meaning'
    assert concept(descriptor, 'length_m') != concept(other, 'length_m')
    graph = vocabulary(descriptor) + vocabulary(other)
    assert (concept(other, 'length_m'), SKOS.definition, Literal('Independent meaning', lang='fr')) in graph
    for group in ('inputs','experiment'):
        for name, spec in descriptor[group].items():
            assert spec['quantity_kind'] and spec['model_component'] and spec['scope_note']
            term = concept(descriptor,name)
            assert (term, WS.quantity, Literal(spec['quantity_kind'])) in graph
            assert (term, SKOS.scopeNote, Literal(spec['scope_note'],lang='fr')) in graph
            assert list(graph.objects(term, SKOS.inScheme))
            assert (term, SKOS.broader, concept(descriptor,'group/'+group)) in graph


def test_run_links_software_activity_scenario_outputs_and_technical_setting(tmp_path):
    session = Session(load_descriptor(ROOT,'tls'))
    session.propose_profile()
    session.accept_profile()
    target, _ = run(session.scenario,session.descriptor,ROOT,tmp_path)
    graph = Graph().parse(target/'semantics.ttl')
    activity = WS['run/'+target.name]
    scenario = WS['scenario/'+target.name]
    assert (activity,RDF.type,PROV.Activity) in graph
    assert (activity,PROV.used,scenario) in graph
    agent = graph.value(activity,PROV.wasAssociatedWith)
    assert (agent,RDF.type,PROV.SoftwareAgent) in graph
    assert graph.value(agent,WS.revision) == Literal(session.descriptor['software']['commit'])
    manifest = json.loads((target/'manifest.json').read_text(encoding='utf-8'))
    for table in manifest['outputs']:
        output=WS[f'{target.name}/outputs/{table}']
        assert (output,PROV.wasGeneratedBy,activity) in graph
        assert list(graph.objects(output,PROV.atLocation))
    seed=WS[f'{target.name}/experiment/base_seed']
    assert (seed,RDF.type,WS.OperationalSetting) in graph
    assert (seed,RDF.type,WS.Hypothesis) not in graph
