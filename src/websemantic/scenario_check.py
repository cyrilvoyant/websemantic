"""SHACL check of an LQL-Equiv scenario before it is computed (web app 0.3.x).

The scenario's values become parameter records (concept, value, group instance), merged with the ontology, and the
shapes of ontology/shapes.ttl are applied without inference, as in evaluation/run_relational_controls.py: record form,
numeric types, declared bounds, complete groups and the dose identity per course. Each course or compared schedule is
one group instance. Only LQL-Equiv is checked here: its parameters are mapped to ontology concepts (variables.csv), the
TLS parameters are not in this version. Nothing is completed or converted. pyshacl and rdflib are optional
dependencies; without them the check says it is unavailable instead of passing.
"""

import hashlib
import time
from pathlib import Path

CONCEPTS = {"dose_per_fraction": "LQL_dose_per_fraction", "n_fractions": "LQL_n_fractions",
            "gap_days": "LQL_gap_days", "total_dose": "LQL_total_dose"}  # total_dose only when the user stated it
_RULES = {}


def _rules(workspace):
    """Ontology (core + LQL-Equiv) and shapes, parsed once per workspace."""
    from rdflib import Graph

    key = str(workspace)
    if key not in _RULES:
        folder = Path(workspace) / "ontology"
        ontology = Graph()
        for name in ("core.ttl", "lqlequiv.ttl"):
            ontology.parse(folder / name, format="turtle")
        shapes = folder / "shapes.ttl"
        _RULES[key] = (ontology, Graph().parse(shapes, format="turtle"), hashlib.sha256(shapes.read_bytes()).hexdigest())
    return _RULES[key]


def records(courses, tumour_site=None, organs=(), reference_dose=None):
    """(concept, value, instance) records of a scenario; courses: dicts with dose_per_fraction, n_fractions, gap_days."""
    out = []
    for i, course in enumerate(courses, 1):
        for field, concept in CONCEPTS.items():
            if course.get(field) is not None:
                out.append((concept, course[field], f"course{i}"))
    if tumour_site:
        out.append(("LQL_tumour_site", str(tumour_site), "1"))
    out += [("LQL_organ", str(o), "1") for o in organs]
    if reference_dose is not None:
        out.append(("LQL_reference_dose", float(reference_dose), "1"))
    return out


def check_lql(workspace, courses, tumour_site=None, organs=(), reference_dose=None):
    """Applies the ontology's shapes to the scenario. Returns status 'conforms', 'violation' or 'unavailable'."""
    try:
        import pyshacl
        from rdflib import BNode, Graph, Literal, Namespace
        from rdflib.namespace import RDF
    except ImportError:
        return {"status": "unavailable", "conforms": None, "messages": []}
    ws, sh = Namespace("https://w3id.org/websemantic/ns#"), Namespace("http://www.w3.org/ns/shacl#")
    start = time.perf_counter()
    ontology, shapes, digest = _rules(workspace)
    rows = records(courses, tumour_site, organs, reference_dose)
    data, named = Graph(), {}
    data.add((ws.Scenario1, RDF.type, ws.Scenario))
    for concept, value, instance in rows:
        node = BNode()
        named[node] = f"{concept} = {value:g}" if isinstance(value, (int, float)) else f"{concept} = {value}"
        named[node] += f" ({instance})" if instance != "1" else ""
        for triple in [(node, RDF.type, ws.Parameter), (node, ws.concept, ws[concept]), (node, ws.value, Literal(value)),
                       (node, ws.groupInstance, Literal(instance)), (ws.Scenario1, ws.hasParameter, node)]:
            data.add(triple)
    conforms, report, _ = pyshacl.validate(data + ontology, shacl_graph=shapes, advanced=True, inference="none")
    messages = set()
    for result in report.subjects(sh.resultMessage, None):  # each message with the record it is about
        focus, text = report.value(result, sh.focusNode), str(report.value(result, sh.resultMessage))
        messages.add(f"{named[focus]}: {text}" if focus in named else text)
    stated_totals = any(c.get("total_dose") is not None for c in courses)
    return {"status": "conforms" if conforms else "violation", "conforms": bool(conforms),
            "messages": sorted(messages), "records": len(rows),
            "relations_not_evaluated": [] if stated_totals else ["total dose per course (no total dose stated)"],
            "shapes": "ontology/shapes.ttl", "shapes_sha256": digest, "engine": f"pyshacl {pyshacl.__version__}",
            "seconds": round(time.perf_counter() - start, 3)}
