import pytest

from websemantic.gemini import GeminiError, load_private_key


def test_private_file_loading(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    (tmp_path / ".env").write_text('# private\nGEMINI_API_KEY="dummy-test-key"\n', encoding="utf-8")
    load_private_key(tmp_path)
    import os

    assert os.environ["GEMINI_API_KEY"] == "dummy-test-key"


def test_environment_has_priority(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-env-key")
    (tmp_path / ".env").write_text("invalid", encoding="utf-8")
    load_private_key(tmp_path)


def test_invalid_file_never_discloses_contents(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    (tmp_path / ".env").write_text("GEMINI_API_KEY=dummy-one\nGEMINI_API_KEY=dummy-two", encoding="utf-8")
    with pytest.raises(GeminiError) as error:
        load_private_key(tmp_path)
    assert "dummy" not in str(error.value)
