from dataclasses import asdict
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import pytest
import yaml

from websemantic import cli, web_research
from websemantic.session import Session

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('url', ['https://localhost/data', 'https://127.0.0.1/', 'http://example.org/', 'https://user:secret@example.org/'])
def test_search_does_not_select_local_or_credential_urls(url):
    assert not web_research.public_url(url)


def test_invalid_citations_are_rejected():
    report = {'answer': 'Explication.', 'limits': '', 'citations': [0]}
    with pytest.raises(ValueError):
        web_research.validate_report(report, [{'status': 'unavailable'}])
    with pytest.raises(ValueError):
        web_research.validate_report({**report, 'citations': [2]}, [{'status': 'consulted'}])


def test_no_supporting_citation_discards_generated_claim():
    report = {'answer': 'Une valeur inventée : 123 kW.', 'limits': '', 'citations': []}
    web_research.validate_report(report, [{'status': 'consulted'}])
    assert '123' not in report['answer']
    assert 'ne permettent pas' in report['answer']


def test_search_does_not_search_for_question_prefix(monkeypatch):
    seen = []

    def response(request, timeout):
        seen.append(request.full_url)
        return BytesIO(b'<rss><channel><item><title>CETU</title><link>https://www.cetu.gouv.fr/</link></item></channel></rss>')

    monkeypatch.setattr(web_research.urllib.request, 'urlopen', response)
    assert web_research.search('Quel rôle joue la ventilation selon le CETU ?')
    query = parse_qs(urlsplit(seen[0]).query)['q'][0]
    assert query.startswith('CETU ') and 'Quel' not in query


def test_web_answer_keeps_values_acceptance_and_run_request(monkeypatch, tmp_path):
    session = Session(yaml.safe_load((ROOT / 'descriptors/tls/descriptor.yaml').read_text(encoding='utf-8')))
    session.propose_profile()
    session.accept_profile()
    session.run_requested = True
    before = asdict(session.scenario)
    report = {'answer': 'Une explication documentée.', 'limits': '', 'citations': [0], 'sources': [
        {'title': 'Source', 'url': 'https://example.org', 'status': 'consulted', 'retrieved_at': '2026-10-03'}]}
    monkeypatch.setattr(cli, 'load_private_key', lambda _: None)
    monkeypatch.setattr(web_research, 'research', lambda *args, **kwargs: report)
    cli.answer_from_web(session, 'cherche la méthode', SimpleNamespace(max_calls=0, workspace=ROOT, output_dir=tmp_path, llm='test'))
    assert asdict(session.scenario) == before
    assert session.run_requested
    assert session.web_reports == [report]
    assert 'https://example.org' in (tmp_path / 'documentation.jsonl').read_text(encoding='utf-8')


@pytest.mark.parametrize('line,automatic', [('/web ventilation électrique tunnel', False), ('Quelles références pour la ventilation ?', False), ('Quel rôle joue la ventilation dans un tunnel ?', True)])
def test_documentary_cli_never_launches_calculation(monkeypatch, line, automatic):
    lines = iter([line, '/q'])
    monkeypatch.setattr('builtins.input', lambda _: next(lines))
    seen = []
    monkeypatch.setattr(cli, 'answer_from_web', lambda session, question, args: seen.append(question))
    monkeypatch.setattr(cli, 'load_private_key', lambda _: None)
    monkeypatch.setattr(cli, 'extract', lambda *args, **kwargs: ({'needs_web': True, 'task': 'unsupported', 'updates': []}, {}))
    monkeypatch.setattr(cli, 'run_if_ready', lambda *args: pytest.fail('A documentary question must not run TLS.'))
    assert cli.main(['chat', '--direct', '--model', 'tls', '--workspace', str(ROOT)]) == 0
    assert seen == [line.split(maxsplit=1)[1] if line.startswith('/web ') else line]


def test_web_needed_calculation_does_not_arm_old_profile(monkeypatch):
    from websemantic.adapters import tls

    lines = iter(['prends les valeurs par défaut', 'Estime un tunnel selon une norme externe', '/v', '/q'])
    monkeypatch.setattr('builtins.input', lambda _: next(lines))
    monkeypatch.setattr(cli, 'load_private_key', lambda _: None)
    monkeypatch.setattr(cli, 'extract', lambda *args, **kwargs: ({'needs_web': True, 'task': 'unsupported', 'updates': []}, {}))
    flags = []
    monkeypatch.setattr(cli, 'answer_from_web', lambda session, question, args: flags.append(session.run_requested))
    monkeypatch.setattr(tls, 'run', lambda *args, **kwargs: pytest.fail('The old profile must not run for an unresolved documentary request.'))
    assert cli.main(['chat', '--direct', '--model', 'tls', '--workspace', str(ROOT)]) == 0
    assert flags == [False]
