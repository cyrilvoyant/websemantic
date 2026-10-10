"""Scalar and relational SHACL checks on the scenarios actually returned by the models (review synthesis, 9 October 2026).

Only answers that decide to execute are checked, for LQL-Equiv and pyrcel (the codes whose parameters are mapped to
ontology concepts). Values are first flattened, without completing or converting anything: an object
(distribution: {N, mu, sigma}), a list of objects (courses, aerosols: one group instance per element) and a dotted or
indexed path (aerosols[1].distribution.N, courses[0].n_fractions) become one record per leaf, with the element index as
group instance. Each leaf is mapped to its concept through the frozen variables.csv; a leaf that cannot be mapped or a
non-numeric value where a number is expected is reported, never invented; a group member that is really absent stays
absent. Both rule
sets of run_relational_controls.py are applied to the same graph (scalar: records, types and bounds; relational: plus
dose identity, same state and complete groups). Each answer is classified as: not evaluable (no mapped value),
valid, scalar violation, or relational violation only (caught by the relations and missed by the scalar checks).
Output (private): e1-validation.csv and a printed summary per model and condition family.
Usage: python validate_answers.py <folder> [...]
"""

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

import pyshacl
from rdflib import BNode, Graph, Literal
from rdflib.namespace import RDF

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "evaluation"))
from run_relational_controls import SH, WS  # noqa: E402

RESERVE = ROOT.parent / "benchmark-reserve"
PACKS = HERE / "frozen-packs-3e89b09"
GROUPED = {"PYR_N", "PYR_mu", "PYR_sigma", "PYR_kappa"}
COURSE = {"LQL_dose_per_fraction", "LQL_n_fractions", "LQL_gap_days", "LQL_total_dose"}
EXTRA = {"total_dose": "LQL_total_dose", "rh": "PYR_RH", "tumour": "LQL_tumour_site"}


def concepts(domain):
    rows = csv.DictReader((PACKS / domain / "variables.csv").open(encoding="utf-8"))
    out = {r["field"].lower(): r["ontology_concept"] for r in rows if r["ontology_concept"]}
    out.update({k: v for k, v in EXTRA.items() if v.startswith(("LQL" if domain == "lqlequiv" else "PYR"))})
    return out


def shapes():
    ontology = Graph()
    for name in ("core.ttl", "lqlequiv.ttl", "pyrcel.ttl"):
        ontology.parse(ROOT / "ontology" / name, format="turtle")
    full = Graph().parse(ROOT / "ontology" / "shapes.ttl", format="turtle")
    scalar = Graph()
    for t in full:
        scalar.add(t)
    for shape in (WS.DerivedQuantityShape, WS.SameQuantityShape, WS.CompleteGroupShape):
        scalar.remove((shape, SH.targetClass, None))
    return ontology, scalar, full


def graph(values):
    g = Graph()
    g.add((WS.Answer, RDF.type, WS.Scenario))
    for concept, value, instance in values:
        node = BNode()
        for t in [(node, RDF.type, WS.Parameter), (node, WS.concept, WS[concept]), (node, WS.value, Literal(value)),
                  (node, WS.groupInstance, Literal(instance)), (WS.Answer, WS.hasParameter, node)]:
            g.add(t)
    return g


REPEATED = {"courses": "course", "aerosols": "mode"}
STEP = re.compile(r"^([a-z_0-9]+)(?:\[([^\]]*)\])?$")


def leaves(field, value, instance=None):
    """Yield (leaf field, value, instance) for one returned value; instance None = default instance."""
    if isinstance(value, dict):
        for key, sub in value.items():
            yield from leaves(f"{field}.{str(key).lower()}", sub, instance)
        return
    head, _, rest = field.partition(".")
    m = STEP.match(head)
    name, index = (m.group(1), m.group(2)) if m else (head, None)
    if isinstance(value, list) and name not in REPEATED:
        for element in value:  # e.g. several organs: one record per element, same instance
            yield from leaves(field, element, instance)
        return
    if name in REPEATED:
        if index is None and isinstance(value, list) and not rest:
            for i, element in enumerate(value):
                yield from leaves(f"{name}[{i}]", element, instance)
            return
        if index is not None:
            instance = REPEATED[name] + (str(int(index) + 1) if index.isdigit() else "-" + index)
            if not rest:
                yield name, value, instance  # e.g. aerosols[0] given as a scalar: reported as unmapped
                return
            yield from leaves(rest, value, instance)
            return
    if name == "distribution" and rest:
        yield from leaves(rest, value, instance)
        return
    yield field, value, instance


def mapped(answer, cmap):
    values, unmapped = [], []
    for v in (answer.get("parsed") or {}).get("values") or []:
        for field, x, instance in leaves(str(v.get("field", "")).lower(), v.get("value")):
            c = cmap.get(field)
            if c is None or x is None or isinstance(x, (list, dict)):
                unmapped.append(field)
                continue
            if isinstance(x, str):
                try:
                    x = float(x.replace(",", "."))
                except ValueError:
                    pass  # categorical value (organ, site): kept as a string literal
            default = "course1" if c in COURSE else "mode1" if c in GROUPED else "1"
            values.append((c, x, instance if instance and (c in COURSE or c in GROUPED) else default))
    return values, unmapped


def classify(answer, cmap, ontology, scalar, full):
    """Status of one executed answer: not evaluable, valid, scalar violation or relational violation only."""
    values, unmapped = mapped(answer, cmap)
    if not values:
        return "not evaluable", "", values, unmapped
    data = graph(values) + ontology
    ok_s, _, _ = pyshacl.validate(data, shacl_graph=scalar, advanced=True, inference="none")
    ok_f, gf, _ = pyshacl.validate(data, shacl_graph=full, advanced=True, inference="none")
    msgs = sorted({str(m) for m in gf.objects(None, SH.resultMessage)})
    status = "valid" if ok_f else "scalar violation" if not ok_s else "relational violation only"
    return status, " | ".join(msgs)[:400], values, unmapped


_RULES = None


def _check(job):
    """One answer (run in a worker process; the rules are loaded once per process)."""
    global _RULES
    if _RULES is None:
        _RULES = shapes(), {d: concepts(d) for d in ("lqlequiv", "pyrcel")}
    (ontology, scalar, full), cmaps = _RULES
    folder, path = job
    a = json.loads(Path(path).read_text(encoding="utf-8"))
    if a.get("domain") not in cmaps or (a.get("parsed") or {}).get("decision") != "execute":
        return None
    status, messages, values, unmapped = classify(a, cmaps[a["domain"]], ontology, scalar, full)
    return {"model": folder.split("__")[0].replace("local_", ""), "case_id": a["case_id"], "domain": a["domain"],
            "condition": a["condition"], "rep": a["rep"], "n_values": len(values),
            "n_instances": len({i for c, _, i in values if c in COURSE or c in GROUPED}),
            "unmapped": ";".join(unmapped), "status": status, "messages": messages}


def main(folders):
    from concurrent.futures import ProcessPoolExecutor

    jobs = [(folder, str(f)) for folder in folders for f in sorted((RESERVE / "runs" / "e1" / folder).glob("*_r[123].json"))]
    with ProcessPoolExecutor() as pool:  # same order as the jobs list
        rows = [r for r in pool.map(_check, jobs, chunksize=16) if r]
    out = HERE / "e1-validation.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    for model in dict.fromkeys(r["model"] for r in rows):
        for dom in ("lqlequiv", "pyrcel"):
            sub = [r for r in rows if r["model"] == model and r["domain"] == dom]
            print(model[:14], dom, len(sub), dict(Counter(r["status"] for r in sub)))
    msg = Counter(m for r in rows for m in r["messages"].split(" | ") if m)
    print("\nmessages:", msg.most_common(8))


if __name__ == "__main__":
    main(sys.argv[1:])
