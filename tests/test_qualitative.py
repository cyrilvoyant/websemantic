from pathlib import Path

import pytest

from websemantic.registry import load_descriptor
from websemantic.session import Session


def session():
    return Session(load_descriptor(Path(__file__).resolve().parents[1], 'tls'))


def apply(state, text, value):
    parsed = {'task': state.scenario.task, 'message': '', 'updates': [
        {'field': 'inputs.traffic_level', 'value': value, 'unit': '1', 'evidence': text}
    ]}
    state.apply(text, parsed)
    return parsed


@pytest.mark.parametrize('phrase,expected', [
    ('beaucoup de trafic', 1.5),
    ('beaucoup de traffic', 1.5),
    ('énormément de trafic', 2.0),
    ('trafic très élevé', 2.0),
])
def test_qualitative_levels_are_locally_resolved_and_require_acceptance(phrase, expected):
    state = session()
    parsed = apply(state, phrase, '99')  # Extraction cannot override the declared scale.
    record = state.scenario.inputs['traffic_level']
    assert record.value == expected
    assert record.origin == 'assumption' and not record.accepted
    assert record.evidence == phrase and '2.0' in record.source
    assert 'à valider' in parsed['message']
    state.accept_profile()
    assert state.scenario.inputs['traffic_level'].accepted


def test_explicit_number_takes_priority():
    state = session()
    apply(state, 'trafic élevé, utilise 1.2', '1.2')
    record = state.scenario.inputs['traffic_level']
    assert record.value == 1.2 and record.origin == 'provided'


@pytest.mark.parametrize('phrase', ['pas beaucoup de trafic', 'sans énormément de trafic',
                                   'beaucoup de trafic ou énormément de trafic'])
def test_ambiguous_or_negative_qualifiers_leave_state_unchanged(phrase):
    state = session()
    with pytest.raises(ValueError):
        apply(state, phrase, 'beaucoup')
    assert 'traffic_level' not in state.scenario.inputs


def test_undeclared_qualifier_is_not_a_numeric_default():
    state = session()
    with pytest.raises(ValueError):
        apply(state, 'trafic moyen', 'moyen')
    assert 'traffic_level' not in state.scenario.inputs


DESCRIPTOR = load_descriptor(Path(__file__).resolve().parents[1], 'tls')
CASES = [(group, name, label, alias, level.get('value') if 'value' in level
          else spec['qualitative_scale']['reference_upper'] * level['fraction'])
         for group in ('inputs', 'experiment') for name, spec in DESCRIPTOR[group].items()
         for label, level in spec.get('qualitative_scale', {}).get('levels', {}).items()
         for alias in level['aliases']]


@pytest.mark.parametrize('group,name,label,alias,expected', CASES)
def test_every_declared_alias_has_a_typed_traceable_value(group, name, label, alias, expected):
    state = session()
    parsed = {'task': state.scenario.task, 'message': '', 'updates': [
        {'field': f'{group}.{name}', 'value': label, 'unit': '', 'evidence': alias}]}
    state.apply(alias, parsed)
    record = getattr(state.scenario, group)[name]
    assert record.value == expected
    if DESCRIPTOR[group][name]['type'] == 'int':
        assert type(record.value) is int
    assert record.unit == DESCRIPTOR[group][name]['unit']
    assert record.origin == 'assumption' and not record.accepted
    assert 'Convention qualitative' in record.source
    state.propose_profile()
    state.accept_profile()
    assert state.result().decision == 'execute'


def test_all_parameters_have_an_interpretation_policy_and_seed_stays_fixed():
    for group in ('inputs', 'experiment'):
        for spec in DESCRIPTOR[group].values():
            assert bool(spec.get('qualitative_scale')) != bool(spec.get('qualitative_policy'))
    state = session()
    assert state.scenario.experiment['base_seed'].value == 42
    assert not DESCRIPTOR['experiment']['base_seed'].get('qualitative_scale')


def test_repeating_synonyms_of_one_level_is_not_a_conflict():
    state = session()
    apply(state, 'beaucoup de trafic, un fort trafic', 'beaucoup')
    assert state.scenario.inputs['traffic_level'].value == 1.5
