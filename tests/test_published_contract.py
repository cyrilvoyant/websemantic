import json
from copy import deepcopy
from pathlib import Path

import pytest
from rdflib import Graph, Literal

from websemantic import replay
from websemantic.registry import load_descriptor
from websemantic.semantics import WS, concept

ROOT = Path(__file__).resolve().parents[1]


def read(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_published_contract_and_rdf_cover_descriptor_and_outputs():
    descriptor = load_descriptor(ROOT, "tls")
    contract = read("ontology/tls-contract.json")
    graph = Graph().parse(ROOT / "ontology/tls-vocabulary.ttl")
    for group in ("inputs", "experiment"):
        assert contract["parameters"][group] == descriptor[group]
        for name, spec in descriptor[group].items():
            assert (concept(descriptor, name), WS.fieldPath, Literal(f"{group}.{name}")) in graph
            assert (concept(descriptor, name), WS.dataType, Literal(spec["type"])) in graph
            for choice in spec.get("values", []):
                assert (concept(descriptor, name), WS.allowedValue, Literal(choice)) in graph
    assert set(contract["output_tables"]) == set(descriptor["outputs"])
    for table, info in contract["output_tables"].items():
        for name, metadata in info["columns"].items():
            assert metadata["meaning"] and metadata["quantity"]
            assert (concept(descriptor, f"outputs/{table}/{name}"), WS.quantity, Literal(metadata["quantity"])) in graph


def test_complete_example_satisfies_json_schema_and_python_gate():
    from jsonschema import Draft202012Validator, FormatChecker

    from websemantic.core.validation import validate

    schema = read("ontology/tls-scenario.schema.json")
    Draft202012Validator.check_schema(schema)
    example = read("examples/tls-complete.json")
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(example)
    assert validate(replay.load_scenario(example), load_descriptor(ROOT, "tls")).decision == "execute"


@pytest.mark.parametrize("change", ["unaccepted", "missing", "unit", "unknown"])
def test_replay_blocks_invalid_records_before_adapter(change, tmp_path, monkeypatch, capsys):
    example = deepcopy(read("examples/tls-complete.json"))
    if change == "unaccepted":
        example["inputs"]["length_m"]["accepted"] = False
    elif change == "missing":
        del example["inputs"]["length_m"]
    elif change == "unit":
        example["inputs"]["length_m"]["unit"] = "km"
    else:
        example["inputs"]["invented"] = example["inputs"]["length_m"]
    file = tmp_path / "scenario.json"
    file.write_text(json.dumps(example), encoding="utf-8")
    monkeypatch.setattr(replay, "execute", lambda *args: pytest.fail("Invalid scenario reached adapter"))
    assert replay.main([str(file), "--model", "tls", "--workspace", str(ROOT)]) == 2
    assert json.loads(capsys.readouterr().out)["decision"] != "execute"


def test_manifest_replay_rejects_changed_software(tmp_path, monkeypatch, capsys):
    manifest = {"scenario": read("examples/tls-complete.json"),
                "software": {"commit": "another-revision"}}
    file = tmp_path / "manifest.json"
    file.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(replay, "execute", lambda *args: pytest.fail("Changed backend reached adapter"))
    assert replay.main([str(file), "--model", "tls", "--workspace", str(ROOT)]) == 2
    assert json.loads(capsys.readouterr().out)["decision"] == "refuse"
