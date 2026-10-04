import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('installation_check', ROOT / 'verifier-installation.py')
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


def test_current_environment_is_compatible():
    assert check.dependencies() == []


def test_newer_dependency_is_kept(monkeypatch):
    original = check.importlib.metadata.version
    monkeypatch.setattr(check.importlib.metadata, 'version', lambda name: '99.0' if name == 'numpy' else original(name))
    assert check.dependencies() == []


@pytest.mark.parametrize('version', [None, '1.20'])
def test_missing_or_old_dependency_has_actionable_diagnostic(monkeypatch, version):
    original = check.importlib.metadata.version

    def installed(name):
        if name != 'numpy':
            return original(name)
        if version is None:
            raise check.importlib.metadata.PackageNotFoundError(name)
        return version

    monkeypatch.setattr(check.importlib.metadata, 'version', installed)
    problems = check.dependencies()
    assert len(problems) == 1 and 'numpy' in problems[0]


def test_missing_backend_does_not_launch_or_install(tmp_path):
    assert 'absents' in check.runtime(tmp_path)[0]


def test_missing_git_is_identified(monkeypatch):
    monkeypatch.setattr(check.shutil, 'which', lambda _: None)
    assert 'Git' in check.runtime(ROOT)[0]


def test_installer_runs_real_tls_smoke_without_llm(monkeypatch):
    from websemantic import gemini

    def forbidden(*args, **kwargs):
        raise AssertionError("No LLM call during installation")

    monkeypatch.setattr(gemini, "extract", forbidden)
    assert check.smoke(ROOT) == []
