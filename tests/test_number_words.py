from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from websemantic.session import Session
from websemantic.units import parse_number


@pytest.mark.parametrize('text,expected', [('deux', 2), ('une', 1), ('zéro', 0), ('dix sept', 17), ('3', 3)])
def test_french_numbers_are_explicitly_normalised(text, expected):
    assert parse_number(text, 'int')[0] == expected


@pytest.mark.parametrize('value', ['plusieurs', 'environ deux', '2.5', 2.5, True])
def test_ambiguous_or_fractional_counts_are_not_invented(value):
    with pytest.raises(ValueError):
        parse_number(value, 'int')


def test_user_two_km_two_tubes_two_lanes_request_is_atomic_and_traced():
    root = Path(__file__).resolve().parents[1]
    session = Session(yaml.safe_load((root / 'descriptors/tls/descriptor.yaml').read_text(encoding='utf-8')))
    request = 'Un tunnel de 2 km, avec deux tubes et deux voies par tube.'
    updates = [
        {'field': 'inputs.length_m', 'value': '2', 'unit': 'km', 'evidence': '2 km'},
        {'field': 'inputs.n_tubes', 'value': 'deux', 'unit': 'unit:NUM', 'evidence': 'deux tubes'},
        {'field': 'inputs.n_lanes_per_tube', 'value': 'deux', 'unit': 'nombre', 'evidence': 'deux voies par tube'},
    ]
    session.apply(request, {'task': session.scenario.task, 'updates': updates})
    assert session.scenario.inputs['length_m'].value == 2000
    for field in ('n_tubes', 'n_lanes_per_tube'):
        assert session.scenario.inputs[field].value == 2
        assert 'Number word normalisation' in session.scenario.inputs[field].source
    assert 'Unit label normalisation' in session.scenario.inputs['n_lanes_per_tube'].source
    before = deepcopy(session.scenario)
    updates[2]['value'] = 'plusieurs'
    with pytest.raises(ValueError):
        session.apply(request, {'task': session.scenario.task, 'updates': updates})
    assert session.scenario == before
