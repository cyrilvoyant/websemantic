"""Length control for the ontology factor (preregistered in evaluation/PREREG-length-control.md).

From the packs frozen at 3e89b09 (evaluation/e1/frozen-packs-3e89b09, the campaign version), build per software:
  ontology-compact.ttl        L2: the software's own semantic content only (parameter definitions with bounds,
                              qualitative conventions and clarification policies, output variables, SKOS concepts
                              (TLS describes its parameters as concepts), intents, tasks, the
                              shared qualitative scale), without the generic core axioms.
  ontology-lengthmatched.ttl  L3: off-topic RDF of the same format and the same length as the full O package
                              (ontology.ttl + shapes.ttl): the other two software's ontologies, repeated if needed,
                              cut at a statement boundary.
Deterministic; the sizes are printed and recorded in length-controls.json.
"""

import json
from pathlib import Path

import rdflib
from rdflib.namespace import RDF

HERE = Path(__file__).resolve().parent
FROZEN = HERE / "frozen-packs-3e89b09"
WS = rdflib.Namespace("https://github.com/cyrilvoyant/websemantic/ns#")
SKOS = rdflib.Namespace("http://www.w3.org/2004/02/skos/core#")
KEEP = (WS.ParameterDefinition, WS.QualifierMapping, WS.ClarificationPolicy, WS.OutputVariable, WS.QualitativeTerm,
        WS.TaskProfile, WS.Contract, WS.ValidityLimit, WS.Intent, SKOS.ConceptScheme, SKOS.Concept)
DOMAINS = ("tls", "lqlequiv", "pyrcel")


def closure(g, node, out):
    """Copy the triples of node, following blank nodes (bounds)."""
    for p, o in g.predicate_objects(node):
        out.add((node, p, o))
        if isinstance(o, rdflib.BNode):
            closure(g, o, out)


def compact(domain):
    g = rdflib.Graph()
    g.parse(FROZEN / domain / "ontology.ttl")
    out = rdflib.Graph()
    for prefix, ns in g.namespaces():
        out.bind(prefix, ns)
    for t in KEEP:
        for s in g.subjects(RDF.type, t):
            closure(g, s, out)
    return out.serialize(format="turtle")


def statements(text):
    """Split Turtle text into prefix lines and complete statements (ending with ' .')."""
    prefixes, body, cur = [], [], []
    for line in text.splitlines():
        if line.startswith("@prefix"):
            prefixes.append(line)
            continue
        cur.append(line)
        if line.rstrip().endswith(" .") or line.rstrip() == ".":
            body.append("\n".join(cur))
            cur = []
    return prefixes, body


def length_matched(domain, target):
    others = [d for d in DOMAINS if d != domain]
    prefixes, body = [], []
    for d in others:
        p, b = statements((FROZEN / d / "ontology.ttl").read_text(encoding="utf-8"))
        prefixes += [x for x in p if x not in prefixes]
        body += b
    head = "\n".join(prefixes) + "\n\n"
    out, i = head, 0
    while len(out) < target:
        nxt = body[i % len(body)] + "\n"
        if len(out) + len(nxt) > target and len(out) > 0.97 * target:
            break
        out += nxt
        i += 1
    return out


def main():
    record = {}
    for d in DOMAINS:
        full = sum(len((FROZEN / d / f).read_text(encoding="utf-8")) for f in ("ontology.ttl", "shapes.ttl"))
        c = compact(d)
        m = length_matched(d, full)
        (FROZEN / d / "ontology-compact.ttl").write_text(c, encoding="utf-8")
        (FROZEN / d / "ontology-lengthmatched.ttl").write_text(m, encoding="utf-8")
        record[d] = {"full_O_chars": full, "compact_chars": len(c), "lengthmatched_chars": len(m)}
        print(d, record[d])
    (FROZEN / "length-controls.json").write_text(json.dumps(record, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
