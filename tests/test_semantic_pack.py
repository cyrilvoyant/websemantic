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
