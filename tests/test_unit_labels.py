from pathlib import Path

import pytest
import yaml

from websemantic.session import Session

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('field,value,label,expected', [
    ('inputs.n_tubes', '2', 'nombre', 'unit:NUM'),
    ('inputs.n_lanes_per_tube', '2', 'number', 'unit:NUM'),
    ('inputs.tunnel_context', 'urban', 'catégorie', None),
    ('inputs.lighting_type', 'LED fixed', 'category', None),
    ('inputs.ventilation_type', 'longitudinal', 'catégorie', None),
    ('experiment.start_date', '2025-01-01', 'date', None),
    ('experiment.base_seed', '42', 'identifiant', None),
    ('experiment.n_days', '30', 'jours', 'unit:DAY'),
    ('experiment.freq_minutes', '15', 'min', 'unit:MIN'),
    ('inputs.morning_peak_hour', '8', 'h du jour', 'unit:HR'),
    ('inputs.altitude_m', '40', 'm', 'unit:M'),
    ('inputs.base_fixed_kw', '40', 'kW', 'unit:KiloW'),
    ('inputs.gradient_percent', '2', '%', 'unit:PERCENT'),
    ('inputs.aux_kw_per_km_tube', '35', 'kW/(km·tube)', 'unit:KiloW per km per tube'),
])
def test_human_type_labels_use_descriptor_units(field, value, label, expected):
    session = Session(yaml.safe_load((ROOT / 'descriptors/tls/descriptor.yaml').read_text(encoding='utf-8')))
    session.propose_profile()
    session.accept_profile()
    session.apply(value, {'task': session.scenario.task, 'updates': [
        {'field': field, 'value': value, 'unit': label, 'evidence': value}]})
    group, name = field.split('.')
    record = getattr(session.scenario, group)[name]
    assert record.unit == expected
    assert 'normalisation' in record.source
    assert session.result().decision == 'execute'


@pytest.mark.parametrize('field,value', [('inputs.n_tubes', '2'), ('inputs.ventilation_type', 'longitudinal'), ('experiment.start_date', '2025-01-01')])
def test_physical_unit_is_not_silently_removed(field, value):
    session = Session(yaml.safe_load((ROOT / 'descriptors/tls/descriptor.yaml').read_text(encoding='utf-8')))
    session.propose_profile()
    session.accept_profile()
    session.apply(value, {'task': session.scenario.task, 'updates': [
        {'field': field, 'value': value, 'unit': 'unit:M', 'evidence': value}]})
    assert session.result().decision == 'clarify'
    assert any(issue.code == 'unit' for issue in session.result().issues)
