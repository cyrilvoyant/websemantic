from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from websemantic.cli import run_if_ready
from websemantic.geography import ALLOWED, apply_report, location
from websemantic.session import Session


@pytest.fixture
def session():
    root = Path(__file__).resolve().parents[1]
    return Session(yaml.safe_load((root / 'descriptors/tls/descriptor.yaml').read_text(encoding='utf-8')))


@pytest.fixture
def report():
    return {
        'city': 'Ajaccio', 'summary': 'Contexte documentaire, sans calibration du tunnel.',
        'sources': [{'url': 'https://example.org/official', 'status': 'consulted', 'retrieved_at': '2026-10-03'}],
        'topics': [{'topic': name, 'explanation': 'Source de test.'} for name in ('trafic', 'pollution', 'accidents', 'pics')],
        'proposals': [{'field': name, 'value': str(value), 'rationale': 'Hypothèse de test, pas une mesure.', 'sources': [0]}
                      for name, value in zip(ALLOWED, ('urban', 1, 8, 18, 1.4))],
    }


def test_city_detection_and_comparison():
    assert location('Comme Àjaccio') == 'ajaccio'
    assert location('un tunnel à PARIS') == 'paris'
    assert location('tunnel rural') is None
    with pytest.raises(ValueError):
        location('Paris ou Ajaccio')


def test_geography_keeps_user_values_and_requires_acceptance(session, report):
    session.apply('pointe à 9 h', {'task': session.scenario.task, 'updates': [
        {'field': 'inputs.morning_peak_hour', 'value': '9', 'unit': 'unit:HR', 'evidence': '9 h'}]})
    apply_report(session, 'comme Ajaccio', report)
    assert session.scenario.inputs['morning_peak_hour'].value == 9
    assert session.scenario.inputs['morning_peak_hour'].origin == 'provided'
    assert session.scenario.inputs['evening_peak_hour'].unit == 'unit:HR'
    assert session.result().decision == 'clarify'
    assert session.scenario.inputs['accident_probability_per_day'].origin == 'default'
    session.accept_profile()
    assert session.result().decision == 'execute'


@pytest.mark.parametrize('bad', ['nan', '-1', '24'])
def test_invalid_hour_is_atomic(session, report, bad):
    before = deepcopy(session.scenario)
    report['proposals'][2]['value'] = bad
    with pytest.raises(ValueError):
        apply_report(session, 'Ajaccio', report)
    assert session.scenario == before


def test_unavailable_source_cannot_support_assumption(session, report):
    report['sources'][0]['status'] = 'unavailable'
    with pytest.raises(ValueError):
        apply_report(session, 'Ajaccio', report)
    assert not session.scenario.inputs


def test_city_cannot_invent_accident_probability(session, report):
    report['proposals'].append({'field': 'accident_probability_per_day', 'value': '0.001', 'rationale': 'petite ville', 'sources': [0]})
    with pytest.raises(ValueError):
        apply_report(session, 'Ajaccio', report)
    assert not session.scenario.inputs


def test_failed_geography_blocks_even_previously_accepted_scenario(session):
    session.propose_profile()
    session.accept_profile()
    session.run_requested = True
    session.geographic_pending = True
    assert run_if_ready(session, SimpleNamespace(), session.descriptor) is None
