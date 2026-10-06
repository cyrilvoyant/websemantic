from pathlib import Path

import pytest

from websemantic import cli

ROOT = Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('choice,namespace', [('1','websemantic.tls'), ('2','websemantic.lql'), ('3','websemantic.pyrcel')])
def test_available_menu_opens_selected_environment_without_llm(choice,namespace,monkeypatch,capsys):
    lines=iter([choice,'/q'])
    monkeypatch.setattr('builtins.input',lambda _:next(lines))
    monkeypatch.setattr(cli,'load_private_key',lambda *a:pytest.fail('Menu must not load a key'))
    monkeypatch.setattr(cli,'extract',lambda *a,**k:pytest.fail('Menu must not call Gemini'))
    assert cli.main(['chat','--workspace',str(ROOT)])==0
    assert namespace in capsys.readouterr().out

def test_quit_menu_does_not_load_descriptor(monkeypatch,tmp_path,capsys):
    monkeypatch.setattr('builtins.input',lambda _:'q')
    assert cli.main(['chat','--workspace',str(tmp_path)])==0
    assert 'Descripteur introuvable' not in capsys.readouterr().out

def test_invalid_choice_repeats_menu(monkeypatch,capsys):
    lines=iter(['9','q']);monkeypatch.setattr('builtins.input',lambda _:next(lines))
    assert cli.choose_environment() is None
    assert capsys.readouterr().out.count('choisissez votre environnement')==2
