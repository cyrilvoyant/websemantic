"""The semantic packs are complete and consistent with the descriptors."""

import csv
import json
from pathlib import Path

import pytest
import yaml
from rdflib import Graph

ROOT = Path(__file__).resolve().parents[1]
FILES = {"LLM-CONTRACT.md", "variables.csv", "units.csv", "outputs.csv", "ontology.ttl", "shapes.ttl", "codemeta.json", "FAIR.md"}


@pytest.mark.parametrize("dom", ["tls", "lqlequiv", "pyrcel"])
def test_pack_complete_and_consistent(dom):
    pack = ROOT / "packs" / dom
    assert {p.name for p in pack.iterdir()} >= FILES
    d = yaml.safe_load((ROOT / "descriptors" / dom / "descriptor.yaml").read_text(encoding="utf-8"))
    fields = [n for g in ("inputs", "experiment") for n in (d.get(g) or {})]
    rows = list(csv.DictReader((pack / "variables.csv").open(encoding="utf-8")))
    assert [r["field"] for r in rows] == fields
    for r in rows:
        if r["unit"]:
            assert r["unit_iri"] and r["quantity_kind_iri"], r["field"]
        assert "=None" not in r["qualitative_conventions_require_acceptance"], r["field"]
    units = list(csv.DictReader((pack / "units.csv").open(encoding="utf-8")))
    assert {u["unit"] for u in units} >= {r["unit"] for r in rows if r["unit"]}
    Graph().parse(pack / "ontology.ttl", format="turtle")
    Graph().parse(pack / "shapes.ttl", format="turtle")
    meta = json.loads((pack / "codemeta.json").read_text(encoding="utf-8"))
    assert meta.get("websemantic:pinnedRevision") == d["software"].get("commit", "")
    assert (pack / "LLM-CONTRACT.md").read_text(encoding="utf-8").startswith("# LLM contract")


@pytest.mark.parametrize("dom", ["tls", "lqlequiv", "pyrcel"])
def test_pack_is_faithful_to_descriptor(dom):
    pack = ROOT / "packs" / dom
    d = yaml.safe_load((ROOT / "descriptors" / dom / "descriptor.yaml").read_text(encoding="utf-8"))
    specs = {n: s for g in ("inputs", "experiment") for n, s in (d.get(g) or {}).items()}
    for r in csv.DictReader((pack / "variables.csv").open(encoding="utf-8")):
        s = specs[r["field"]]
        assert r["unit"] == (s.get("unit") or ""), r["field"]
        assert r["default_proposal"] == str(s.get("default", "")), r["field"]
        bounds = "; ".join(f"{k} {v}" for k, v in (s.get("bounds") or {}).items() if k != "authority")
        assert r["bounds"] == bounds, r["field"]
    outputs = list(csv.DictReader((pack / "outputs.csv").open(encoding="utf-8")))
    assert outputs and {"aggregation", "temporal_support", "additive", "validity_flag", "unit_source"} <= set(outputs[0])
    declared = {n for n, o in (d.get("outputs") or {}).items() if isinstance(o, dict)}
    assert declared <= {o["output"] for o in outputs}
    units = {u["unit"]: u for u in csv.DictReader((pack / "units.csv").open(encoding="utf-8"))}
    for o in outputs:
        if o["unit"]:
            assert o["unit"] in units, o["output"]
    for u in units.values():
        assert (u["source"] == "QUDT") == u["iri"].startswith("http://qudt.org/vocab/unit/")
