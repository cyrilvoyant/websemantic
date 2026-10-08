"""Validate the reviewed contextual control before any provider call."""
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import rdflib

ROOT = Path(__file__).resolve().parents[1]


def runner():
    spec = importlib.util.spec_from_file_location("length_runner", ROOT / "evaluation/e1/run_e1.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("domain", ["tls", "lqlequiv", "pyrcel"])
def test_contexts_reproduce_reviewed_artifacts(domain):
    module = runner()
    expected = json.loads((module.FROZEN_PACKS / "reviewed-contexts.json").read_text())
    for condition in ("L2", "L3", "FROZEN-F010", "FROZEN-F110"):
        text = module.length_context(domain, condition)
        assert hashlib.sha256(text.encode()).hexdigest() == expected["contexts"][domain][condition]
    for name in ("ontology.ttl", "shapes.ttl", "ontology-compact.ttl", "ontology-lengthmatched.ttl"):
        assert len(rdflib.Graph().parse(module.FROZEN_PACKS / domain / name, format="turtle")) > 0


def test_changed_pack_refused_before_collection(tmp_path):
    module = runner()
    shutil.copytree(module.FROZEN_PACKS, tmp_path / "packs")
    module.FROZEN_PACKS = tmp_path / "packs"
    path = module.FROZEN_PACKS / "tls/ontology-compact.ttl"
    path.write_text(path.read_text(encoding="utf-8") + "\n# alteration", encoding="utf-8")
    with pytest.raises(ValueError, match="Frozen source changed"):
        module.length_context("tls", "L2")


def test_native_doc_drift_refused(monkeypatch):
    module = runner()
    monkeypatch.setattr(module, "native_doc", lambda domain: "changed native API")
    with pytest.raises(ValueError, match="Frozen context changed"):
        module.length_context("tls", "L3")


def test_typo_never_becomes_contract_baseline():
    with pytest.raises(ValueError, match="Unknown frozen"):
        runner().length_context("tls", "L4")


def test_cli_preflight_all_conditions_without_collection():
    result = subprocess.run([sys.executable, str(ROOT / "evaluation/e1/run_e1.py"),
                             "--conditions", "L2,L3,FROZEN-F010,FROZEN-F110", "--check-contexts"],
                            capture_output=True, text=True, check=True)
    report = json.loads(result.stdout)
    assert len(report) == 12
    assert report["tls|FROZEN-F010"]["sha256"].startswith("aecac2766b8a")
    assert report["pyrcel|FROZEN-F110"]["sha256"].startswith("286f0806457a")
