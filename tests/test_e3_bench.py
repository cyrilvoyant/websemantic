"""Synthetic fixtures only: these tests are not E3 experimental results."""

import hashlib
import json

import pytest

from evaluation.e3.bench import numeric_score, prepare, score, source_category


def artifact(root, name, text="synthetic fixture", kind=None):
    path = root / name
    path.write_text(text, encoding="utf-8")
    result = {"path": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    if kind:
        result["kind"] = kind
    return result


@pytest.fixture
def case():
    return {"id": "synthetic-TLS", "request": "Synthetic fixture, do not use in campaign",
            "official_url": "https://github.com/example/tls",
            "websemantic_url": "https://github.com/example/websemantic",
            "reference_outputs": [{"quantity": "energy", "unit": "MWh",
                                   "support": "2025-01:monthly", "values": [2, 4]}]}


def record(tmp_path, case):
    return {"id": "fixture1", "case_id": case["id"], "mode": "open_web",
            "entry_assignment": "two_links", "fair_assignment": "uncontrolled",
            "model": "synthetic", "tools": ["synthetic"], "fresh_session": True,
            "time_utc": "2026-10-08T00:00:00Z",
            "response_artifact": artifact(tmp_path, "response.txt")}


def test_prepare_preserves_baseline_and_does_not_modify_origin(tmp_path, case):
    origin = tmp_path / "origin"
    origin.mkdir()
    artifact(origin, "README.md", "science")
    artifact(origin, "CITATION.cff", "citation")
    config = {"cases": [case], "candidates": [{"id": "A", "root": str(origin),
              "scientific_files": ["README.md"], "fair_files": ["CITATION.cff"]}]}
    out = tmp_path / "private-snapshot"
    prepare(config, out)
    assert (origin / "README.md").read_text() == "science"
    assert (out / "fair0/A/README.md").read_bytes() == (out / "fair1/A/README.md").read_bytes()
    assert not (out / "fair0/A/CITATION.cff").exists()
    assert (out / "fair1/A/CITATION.cff").exists()
    prompts = json.loads((out / "prompts.json").read_text())
    assert len(prompts) == 4
    assert {p["fair_assignment"] for p in prompts if p["mode"] == "open_web"} == {"uncontrolled"}
    with pytest.raises(ValueError, match="already exists"):
        prepare(config, out)


def test_contract_is_not_a_fair_only_intervention(tmp_path, case):
    config = {"cases": [case], "candidates": [{"id": "A", "root": str(tmp_path),
              "scientific_files": ["README.md"], "fair_files": ["LLM-CONTRACT.md"]}]}
    with pytest.raises(ValueError, match="only accepts"):
        prepare(config, tmp_path / "out")


def test_citation_and_execution_claim_alone_prove_neither(tmp_path, case):
    obs = record(tmp_path, case)
    obs.update(cited_sources=[case["websemantic_url"]], execution={"claimed": True})
    result = score(obs, case, tmp_path)
    assert result["cited_categories"] == ["websemantic"]
    assert result["observed_first_entry"] == "unobserved"
    assert not result["execution_bundle_verified"]
    assert not result["archived_bundle_and_numeric_match"]


def test_opened_capture_and_reading_annotation(tmp_path, case):
    obs = record(tmp_path, case)
    obs["response_artifact"] = artifact(tmp_path, "response.txt", "energy 4 MWh")
    capture = artifact(tmp_path, "source.txt", "canonical unit: MWh")
    obs["opened_sources"] = [{"url": case["official_url"], "capture": capture},
                             {"url": case["websemantic_url"], "capture": capture}]
    obs["reading_evidence"] = [{"capture": capture, "source_quote": "MWh",
                                "response_quote": "MWh", "annotation": "supported"}]
    result = score(obs, case, tmp_path)
    assert result["observed_first_entry"] == "official"
    assert result["supported_reading_annotations"] == 1
    (tmp_path / "source.txt").write_text("changed")
    assert score(obs, case, tmp_path)["observed_first_entry"] == "unobserved"


def test_bundle_and_comparable_numbers(tmp_path, case):
    obs = record(tmp_path, case)
    obs["execution"] = {"claimed": True, "artifacts": [
        artifact(tmp_path, kind + ".txt", kind=kind)
        for kind in ("scenario", "manifest", "outputs", "execution_log")]}
    obs["reported_outputs"] = case["reference_outputs"]
    assert score(obs, case, tmp_path)["archived_bundle_and_numeric_match"]
    obs["reported_outputs"] = [{**case["reference_outputs"][0], "unit": "kWh"}]
    assert not score(obs, case, tmp_path)["archived_bundle_and_numeric_match"]


def test_numeric_rms_denominator_and_missing_support(case):
    expected = case["reference_outputs"]
    result = numeric_score(expected, [{**expected[0], "values": [3, 5]}])[0]
    assert result["rmsd"] == 1
    assert result["nRMSD_rms"] == pytest.approx(1 / (10 ** .5))
    assert numeric_score(expected, [{**expected[0], "support": "other"}])[0]["rmsd"] is None
    assert numeric_score(expected, [{**expected[0], "values": [float("nan"), 2]}])[0]["rmsd"] is None


def test_public_fair_assignment_is_not_controlled(tmp_path, case):
    obs = record(tmp_path, case)
    obs["fair_assignment"] = "fair0"
    with pytest.raises(ValueError, match="cannot be assigned"):
        score(obs, case, tmp_path)


def test_url_boundary_and_raw(case):
    assert source_category(case["official_url"] + "-fake", case) == "other"
    assert source_category("https://raw.githubusercontent.com/example/tls/sha/file.py", case) == "official"


def test_raw_response_integrity_and_case_identity(tmp_path, case):
    obs = record(tmp_path, case)
    obs["case_id"] = "other"
    with pytest.raises(ValueError, match="differ"):
        score(obs, case, tmp_path)
    obs["case_id"] = case["id"]
    obs["response_artifact"]["path"] = "../outside.txt"
    with pytest.raises(ValueError, match="unavailable"):
        score(obs, case, tmp_path)
