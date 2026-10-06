"""Paired mechanism control: scalar checks versus scalar plus relational SHACL.

Hand-built development cases, not LLM responses or held-out performance.
Both conditions use the identical data/ontology, with no OWL inference.
"""

import hashlib
import json
from pathlib import Path

import pyshacl
from rdflib import BNode, Graph, Literal, Namespace
from rdflib.namespace import RDF

ROOT = Path(__file__).resolve().parents[1]
WS = Namespace("https://github.com/cyrilvoyant/websemantic/ns#")
SH = Namespace("http://www.w3.org/ns/shacl#")


def records(values):
    graph = Graph()
    graph.add((WS.Control, RDF.type, WS.Scenario))
    for concept, value, instance in values:
        node = BNode()
        for triple in [(node, RDF.type, WS.Parameter), (node, WS.concept, WS[concept]),
                       (node, WS.value, Literal(value)), (node, WS.groupInstance, Literal(instance)),
                       (WS.Control, WS.hasParameter, node)]:
            graph.add(triple)
    return graph


def fixtures():
    cases = []
    for i, (dose, number) in enumerate([(2., 25), (3., 20), (2.5, 16), (4., 10)]):
        for invalid in (False, True):
            values = [("LQL_dose_per_fraction", dose, "course1"),
                      ("LQL_n_fractions", number, "course1"),
                      ("LQL_total_dose", dose * number + (6. if invalid else 0.), "course1")]
            cases.append({"id": f"dose-{i}-{invalid}", "family": "dose identity",
                          "invalid": invalid, "values": values})
    base = [("PYR_V", 1., "1"), ("PYR_T0", 283., "1"), ("PYR_P0", 85000., "1")]
    mode = [("PYR_N", 1000., "mode1"), ("PYR_mu", .05, "mode1"),
            ("PYR_sigma", 2., "mode1"), ("PYR_kappa", .54, "mode1")]
    for i, rh in enumerate([.98, .95, .90, .85]):
        for invalid in (False, True):
            values = base + mode + [("PYR_RH", rh, "1"),
                                    ("PYR_S0", rh - 1 + (.02 if invalid else 0.), "1")]
            cases.append({"id": f"humidity-{i}-{invalid}", "family": "same state",
                          "invalid": invalid, "values": values})
    for i, missing in enumerate(["PYR_N", "PYR_mu", "PYR_sigma", "PYR_kappa"]):
        for invalid in (False, True):
            values = base + [("PYR_S0", -.02, "1")] + [
                item for item in mode if not invalid or item[0] != missing]
            cases.append({"id": f"group-{i}-{invalid}", "family": "complete aerosol mode",
                          "invalid": invalid, "values": values})
    return cases


def main():
    ontology = Graph()
    for name in ("core.ttl", "lqlequiv.ttl", "pyrcel.ttl"):
        ontology.parse(ROOT / "ontology" / name, format="turtle")
    full = Graph().parse(ROOT / "ontology/shapes.ttl", format="turtle")
    scalar = Graph()
    for triple in full:
        scalar.add(triple)
    # Keep record identity, numeric type, bounds and instance identifiers identical.
    # Disable only the three relational targets, not their input facts.
    for shape in (WS.DerivedQuantityShape, WS.SameQuantityShape, WS.CompleteGroupShape):
        scalar.remove((shape, SH.targetClass, None))
    rows = []
    for fixture in fixtures():
        row = dict(fixture)
        for condition, shapes in (("scalar", scalar), ("relational", full)):
            conforms, graph, _ = pyshacl.validate(records(fixture["values"]) + ontology,
                shacl_graph=shapes, advanced=True, inference="none")
            row[condition] = {"conforms": bool(conforms),
                              "messages": sorted(str(v) for v in graph.objects(None, SH.resultMessage))}
        rows.append(row)
    summary = {}
    for condition in ("scalar", "relational"):
        summary[condition] = {"invalid_detected": sum(r["invalid"] and not r[condition]["conforms"] for r in rows),
                              "invalid_total": sum(r["invalid"] for r in rows),
                              "valid_rejected": sum(not r["invalid"] and not r[condition]["conforms"] for r in rows),
                              "valid_total": sum(not r["invalid"] for r in rows)}
    report = {"scope": "Hand-built paired SHACL mechanism controls; no LLM effect or general success estimate",
              "inference": "none", "summary": summary, "cases": rows,
              "files_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in (ROOT / "ontology").glob("*.ttl")}}
    output = ROOT / "evaluation/relational-controls-20261006.json"
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    assert summary["scalar"] == {"invalid_detected": 0, "invalid_total": 12, "valid_rejected": 0, "valid_total": 12}
    assert summary["relational"] == {"invalid_detected": 12, "invalid_total": 12, "valid_rejected": 0, "valid_total": 12}


if __name__ == "__main__":
    main()
