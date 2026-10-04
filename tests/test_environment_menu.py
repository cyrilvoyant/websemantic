from pathlib import Path

import pytest

from websemantic import cli

ROOT = Path(__file__).resolve().parents[1]


def test_future_choices_repeat_menu_without_llm_or_backend(monkeypatch, capsys):
    lines = iter(['2', '3', '9', '1', '/q'])
    monkeypatch.setattr('builtins.input', lambda _: next(lines))
    monkeypatch.setattr(cli, 'load_private_key', lambda *args: pytest.fail('Menu choices must not load a key.'))
    monkeypatch.setattr(cli, 'extract', lambda *args, **kwargs: pytest.fail('Menu choices must not call Gemini.'))
    assert cli.main(['chat', '--workspace', str(ROOT)]) == 0
    output = capsys.readouterr().out
    assert 'websemantic.lql — Work in progress.' in output
    assert 'websemantic.pvlib — Work in progress.' in output
    assert output.count('choisissez votre environnement') == 4
    assert output.count('WebSemantic — TLS') == 1


def test_quit_menu_does_not_load_descriptor(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr('builtins.input', lambda _: 'q')
    assert cli.main(['chat', '--workspace', str(tmp_path)]) == 0
    assert 'Descripteur introuvable' not in capsys.readouterr().out


@pytest.mark.parametrize('model', ['lql', 'pvlib'])
def test_unavailable_noninteractive_model_does_not_fall_back_to_tls(model, tmp_path, capsys):
    assert cli.main(['chat', '--model', model, '--once', 'calcule', '--workspace', str(tmp_path)]) == 2
    output = capsys.readouterr().out
    assert f'websemantic.{model} — Work in progress.' in output
    assert 'websemantic.tls /' not in output
