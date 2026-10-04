import importlib.util
import sys
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from websemantic import cli
from websemantic.conversation import validate_questions
from websemantic.registry import load_descriptor
from websemantic.session import Session

ROOT = Path(__file__).resolve().parents[1]
DESCRIPTOR = load_descriptor(ROOT, 'tls')


def question(blocking=True):
    return {'question': 'Pour ce scénario fictif, une faible probabilité ou le défaut ?',
            'fields': ['inputs.accident_probability_per_day'], 'blocking': blocking}


def test_uncertainty_survives_readonly_turns_and_generic_acceptance():
    state = Session(deepcopy(DESCRIPTOR))
    state.propose_profile()
    state.accept_profile()
    state.add_questions([question()])
    state.apply('Montre le tableau', {'task': state.scenario.task, 'updates': []})
    assert state.pending_clarification
    before = state.scenario
    state.local_intent('Prends les valeurs par défaut')
    assert state.scenario == before and state.questions
    state.run_requested = True
    assert cli.run_if_ready(state, SimpleNamespace(), state.descriptor) is None


def test_short_answer_uses_question_context_but_still_needs_acceptance():
    state = Session(deepcopy(DESCRIPTOR))
    state.add_questions([question(False)])
    state.apply('Peu', {'task': state.scenario.task, 'updates': [{
        'field': 'inputs.accident_probability_per_day', 'value': 'faible', 'unit': '', 'evidence': 'Peu'}]})
    record = state.scenario.inputs['accident_probability_per_day']
    assert record.value == pytest.approx(.015 * .25)
    assert record.origin == 'assumption' and not record.accepted
    assert not state.questions and not state.pending_clarification


def test_malformed_question_is_atomic():
    state = Session(deepcopy(DESCRIPTOR))
    before = state.scenario
    with pytest.raises(ValueError):
        state.apply('test', {'task': state.scenario.task, 'updates': [],
                            'questions': [{'question': 'Choix ?', 'fields': ['unknown'], 'blocking': True}]})
    assert state.scenario == before
    with pytest.raises(ValueError):
        validate_questions([question()] * 3, state.descriptor)


@pytest.mark.parametrize('reply', ['Le défaut', 'Pour les accidents, garde le défaut.'])
def test_targeted_default_reply_closes_only_its_question(reply):
    state = Session(deepcopy(DESCRIPTOR))
    state.add_questions([question()])
    state.apply(reply, {'task': state.scenario.task, 'updates': [{
        'field': 'inputs.accident_probability_per_day', 'value': '.015', 'unit': '', 'evidence': reply}]})
    record = state.scenario.inputs['accident_probability_per_day']
    assert record.value == .015 and record.origin == 'assumption' and not record.accepted
    assert not state.questions and not state.pending_clarification


def test_review_table_distinguishes_default_retained_value_and_unit(capsys):
    state = Session(deepcopy(DESCRIPTOR))
    state.propose_profile()
    state.set_value('inputs.length_m', '2000')
    cli.details(state)
    output = capsys.readouterr().out
    assert 'Défaut' in output and 'Retenue' in output and 'Origine / état' in output
    row = next(line for line in output.splitlines() if line.startswith('Longueur'))
    assert '1500' in row and '2000' in row and '| m ' in row
    assert 'Graine' not in output


def test_formulas_and_coefficients_match_pinned_backend(capsys):
    path = ROOT / 'external/tunnel-load-simulator/src/tunnel_load_simulator/simulator.py'
    spec = importlib.util.spec_from_file_location('guided_study_tls', path)
    backend = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = backend
    spec.loader.exec_module(backend)
    coefficients = DESCRIPTOR['model_coefficients']
    assert coefficients['lighting'] == {name: list(value) for name,value in backend.LIGHTING_PARAMS.items()}
    assert coefficients['ventilation_kw_per_km_tube'] == backend.VENTILATION_PARAMS
    assert coefficients['context'] == backend.CONTEXT_MULT
    assert list(coefficients['season'].values()) == list(backend.SEASON_FACTORS)
    assert np.allclose(backend.gaussian_peak(np.array([7, 8, 9]), 8, 1, 1),
                       np.exp(-.5 * ((np.array([7, 8, 9]) - 8) / 1) ** 2))
    cli.formulas(Session(deepcopy(DESCRIPTOR)))
    output = capsys.readouterr().out
    assert 'E_ann' in output and 'MWh/an' in output and '365/n_days' in output
