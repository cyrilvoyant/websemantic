import json
from pathlib import Path

from websemantic import cli

ROOT = Path(__file__).resolve().parents[1]


def test_acceptance_and_changed_parameter_run_with_concise_saved_summary(monkeypatch, capsys, tmp_path):
    lines = iter(['/p', '/v', '/set inputs.length_m 2000', '/d', '/q'])
    monkeypatch.setattr('builtins.input', lambda _: next(lines))
    assert cli.main(['chat', '--direct', '--workspace', str(ROOT), '--output-dir', str(tmp_path)]) == 0
    paths = sorted(tmp_path.iterdir())
    assert len(paths) == 2
    text = capsys.readouterr().out
    assert text.count('Dossier des résultats :') == 2
    assert 'consommation annuelle extrapolée' in text
    assert 'longueur 2000 m' in text
    for noise in ('Demande ->', 'Appels Gemini :', 'Gemini interprete', 'Graine'):
        assert noise not in text
    changed = next(path for path in paths if json.loads((path / 'manifest.json').read_text())['scenario']['inputs']['length_m']['value'] == 2000)
    manifest = json.loads((changed / 'manifest.json').read_text())
    assert 'base_seed' in manifest['scenario']['experiment']
    history = json.loads((changed / 'conversation.json').read_text())['history']
    assert any(item['user'].startswith('/set ') for item in history)


def test_natural_parameter_change_recalculates_but_question_does_not(monkeypatch, capsys, tmp_path):
    lines = iter(['/p', '/v', 'Passe la longueur à 2 km', 'Que représente le trafic relatif ?', '/q'])
    monkeypatch.setattr('builtins.input', lambda _: next(lines))
    monkeypatch.setattr(cli, 'load_private_key', lambda _: None)

    def extract(request, descriptor, *args, **kwargs):
        updates = [{'field': 'inputs.length_m', 'value': '2', 'unit': 'km', 'evidence': '2 km'}] if '2 km' in request else []
        return {'task': descriptor['tasks']['supported'][0], 'updates': updates, 'message': 'Explication.', 'needs_web': False}, {}

    monkeypatch.setattr(cli, 'extract', extract)
    assert cli.main(['chat', '--direct', '--workspace', str(ROOT), '--output-dir', str(tmp_path)]) == 0
    assert len(list(tmp_path.iterdir())) == 2
    assert capsys.readouterr().out.count('Dossier des résultats :') == 2


def test_summary_uses_saved_city_not_changed_session(monkeypatch, capsys, tmp_path):
    import yaml

    from websemantic.session import Session

    descriptor = yaml.safe_load((ROOT / 'descriptors/tls/descriptor.yaml').read_text(encoding='utf-8'))
    session = Session(descriptor)
    session.propose_profile()
    session.accept_profile()
    session.geographic_context = {'city': 'Paris'}
    from types import SimpleNamespace

    target, medians = cli.run_if_ready(session, SimpleNamespace(workspace=ROOT, output_dir=tmp_path, open_results=False, model='tls', llm='fixture'), descriptor)
    capsys.readouterr()
    session.geographic_context = {'city': 'Ajaccio'}
    session.set_value('inputs.length_m', '9999')
    cli.results_table(session, target, medians)
    text = capsys.readouterr().out
    assert 'pour un tunnel à Paris' in text
    assert 'Ajaccio' not in text and '9999' not in text
