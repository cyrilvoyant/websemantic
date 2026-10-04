import json
from pathlib import Path

import pandas as pd

from websemantic import cli
from websemantic.adapters.tls import run
from websemantic.registry import load_descriptor
from websemantic.session import Session

ROOT = Path(__file__).resolve().parents[1]


def test_seed_is_fixed_authorized_and_preserved_until_explicit_change(capsys):
    session = Session(load_descriptor(ROOT, 'tls'))
    seed = session.scenario.experiment['base_seed']
    assert seed.value == 42 and seed.accepted and seed.source
    cli.show(session)
    cli.details(session)
    assert 'Graine' not in capsys.readouterr().out
    session.apply('un tunnel de 2 km', {'task': session.scenario.task, 'updates': [
        {'field': 'inputs.length_m', 'value': '2', 'unit': 'km', 'evidence': '2 km'}]})
    session.propose_profile()
    session.accept_profile()
    assert session.scenario.experiment['base_seed'] == seed
    session.apply('Fixe la graine à 123', {'task': session.scenario.task, 'updates': [
        {'field': 'experiment.base_seed', 'value': '123', 'unit': '', 'evidence': '123'}]})
    session.propose_profile()
    assert session.scenario.experiment['base_seed'].value == 123
    cli.details(session, full=True)
    assert 'Graine' in capsys.readouterr().out


def test_csv_and_manifest_retain_fixed_and_changed_seed(tmp_path):
    session = Session(load_descriptor(ROOT, 'tls'))
    session.propose_profile()
    session.accept_profile()
    for seed in (42, 123):
        if seed != 42:
            session.set_value('experiment.base_seed', str(seed))
        target, _ = run(session.scenario, session.descriptor, ROOT, tmp_path)
        csv = pd.read_csv(target/'kpis.csv')
        assert csv.base_seed.tolist() == [seed] * 3
        assert csv.seed.tolist() == [seed, seed+1, seed+2]
        manifest = json.loads((target/'manifest.json').read_text(encoding='utf-8'))
        assert manifest['scenario']['experiment']['base_seed']['value'] == seed
        assert manifest['output_qualification']['tables']['kpis']['columns']['base_seed']['quantity'] == 'identifier'
