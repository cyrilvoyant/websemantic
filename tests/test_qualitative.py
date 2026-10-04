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
