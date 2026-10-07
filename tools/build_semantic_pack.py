"""Build the semantic pack of each software: packs/<software>/.

A pack can be placed next to any unmodified scientific code. Everything is generated
from descriptors/, ontology/ and the pinned sources, so the files cannot disagree.

  LLM-CONTRACT.md  rules + qualitative conventions (read first)
  variables.csv    FAIR description of each input (API name, definition, QUDT unit and
                   quantity kind, bounds with authority, default as proposal, qualifiers)
  units.csv        every unit used, QUDT IRI or local definition, accepted exact conversions
  outputs.csv      meaning, unit, aggregation, temporal support, additivity, validity flags
  ontology.ttl     common core + domain extension
  shapes.ttl       SHACL checks
  codemeta.json    FAIR identity of the original software (pinned revision)
"""

import csv
import io
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
QUDT = "http://qudt.org/vocab/unit/"
QK = "http://qudt.org/vocab/quantitykind/"
DOMAINS = {"tls": "tunnel-load-simulator", "lqlequiv": "LQL-Equiv-web", "pyrcel": "pyrcel"}
EXT_TTL = {"tls": "tls-vocabulary.ttl", "lqlequiv": "lqlequiv.ttl", "pyrcel": "pyrcel.ttl"}

# unit token -> (symbol, QUDT IRI or local IRI, quantity kind IRI, exact conversions accepted from user wording)
UNITS = {
    "unit:M": ("m", QUDT + "M", QK + "Length", "km x1000; cm x0.01"),
    "unit:MicroM": ("µm", QUDT + "MicroM", QK + "Length", "nm x0.001; m x1e6"),
    "unit:KiloW": ("kW", QUDT + "KiloW", QK + "Power", "W x0.001; MW x1000"),
    "unit:KiloW per km per tube": ("kW/(km·tube)", "https://github.com/cyrilvoyant/websemantic/ns#KiloW-PER-KiloM-PER-TUBE",
                                   QK + "Power", "not in QUDT: power per km of one tube; 1 kW/km = 1 W/m"),
    "unit:PERCENT": ("%", QUDT + "PERCENT", QK + "DimensionlessRatio", "fraction x100 (never mix % and fraction)"),
    "unit:UNITLESS": ("1", QUDT + "UNITLESS", QK + "Dimensionless", "percent /100 when the field is a fraction"),
    "unit:NUM": ("count", QUDT + "NUM", QK + "Count", "number words (deux -> 2)"),
    "unit:HR": ("h", QUDT + "HR", QK + "Time", "7 h 30 -> 7.5; min /60"),
    "unit:MIN": ("min", QUDT + "MIN", QK + "Time", "h x60; 'pas horaire' -> 60"),
    "unit:SEC": ("s", QUDT + "SEC", QK + "Time", "min x60"),
    "unit:DAY": ("d", QUDT + "DAY", QK + "Time", "week x7"),
    "unit:GRAY": ("Gy", QUDT + "GRAY", QK + "AbsorbedDose", "cGy x0.01"),
    "unit:K": ("K", QUDT + "K", QK + "ThermodynamicTemperature", "°C +273.15"),
    "unit:PA": ("Pa", QUDT + "PA", QK + "Pressure", "hPa x100; kPa x1000"),
    "unit:M-PER-SEC": ("m/s", QUDT + "M-PER-SEC", QK + "Velocity", "km/h /3.6"),
    "unit:PER-CentiM3": ("cm⁻³", QUDT + "PER-CentiM3", QK + "NumberDensity", "m⁻³ x1e-6"),
}


def descriptor(dom):
    return yaml.safe_load((ROOT / "descriptors" / dom / "descriptor.yaml").read_text(encoding="utf-8"))


def qualifiers(spec):
    scale = spec.get("qualitative_scale") or {}
    out = []
    for level, v in (scale.get("levels") or {}).items():
        value = v.get("value")
        if value is None and "fraction" in v and "reference_upper" in scale:
            value = round(v["fraction"] * scale["reference_upper"], 6)
        out.append(f"{level}={value} [{' / '.join(v.get('aliases', []))}]")
    return " ; ".join(out)


def variables_csv(dom, d):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["group", "field", "api_name", "ontology_concept", "type", "unit", "unit_symbol", "unit_iri", "quantity_kind_iri",
                "bounds", "bound_authority", "categories", "default_proposal", "qualitative_conventions_require_acceptance",
                "course_or_mode_instance", "definition"])
    for group in ("inputs", "experiment"):
        for name, s in (d.get(group) or {}).items():
            u = s.get("unit")
            sym, iri, qk, _ = UNITS.get(u, ("", "", "", ""))
            bounds = s.get("bounds") or {}
            w.writerow([group, name, name, s.get("ontology_concept", ""), s.get("type", ""), u or "", sym, iri, qk,
                        "; ".join(f"{k} {v}" for k, v in bounds.items() if k != "authority"), bounds.get("authority", ""),
                        " | ".join(map(str, s.get("values", []))), s.get("default", ""), qualifiers(s),
                        s.get("group_instance", ""), (s.get("definition") or "").replace("\n", " ")])
    return buf.getvalue()


def units_csv(d):
    used = {s.get("unit") for g in ("inputs", "experiment") for s in (d.get(g) or {}).values() if s.get("unit")}
    for o in (d.get("outputs") or {}).values():
        if isinstance(o, dict) and o.get("unit") in UNITS:
            used.add(o["unit"])
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["unit", "symbol", "iri", "in_qudt", "quantity_kind_iri", "accepted_exact_conversions"])
    for u in sorted(used):
        if u not in UNITS:
            raise ValueError(f"unit {u} missing from the pack table")
        sym, iri, qk, conv = UNITS[u]
        w.writerow([u, sym, iri, int(iri.startswith(QUDT)), qk, conv])
    return buf.getvalue()


def outputs_csv(dom, d):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["output", "ontology_concept", "unit", "unit_symbol", "definition"])
    outs = d.get("outputs") or {}
    for name, o in outs.items():
        if isinstance(o, dict):
            u = o.get("unit")
            w.writerow([name, o.get("ontology_concept", ""), u or "", o.get("display_unit") or UNITS.get(u, ("",))[0],
                        (o.get("definition") or o.get("meaning") or "").replace("\n", " ")])
        else:
            w.writerow([name, "", "", "", str(o).replace("\n", " ")])
    if dom == "tls":  # column-level qualification reviewed against the pinned TLS implementation
        from websemantic.adapters.tls_outputs import column_metadata
        for table, cols in {"representative": ["power_kw", "energy_kwh", "traffic_index", "pollution_event", "accident_event"],
                            "kpis": ["total_mwh", "annualized_mwh", "peak_kw", "load_factor", "specific_kwh_m_year",
                                     "n_pollution_events", "n_accident_events"],
                            "daily": ["energy_kwh", "mean_kw"]}.items():
            for c in cols:
                m = column_metadata(c, table)
                w.writerow([f"{table}.{c}", "", "", m["unit"] or "", f"{m['quantity']}: {m['meaning']}"])
    return buf.getvalue()


def codemeta(dom, d):
    src = ROOT / "external" / DOMAINS[dom]
    cm = src / "codemeta.json"
    meta = json.loads(cm.read_text(encoding="utf-8")) if cm.exists() else {
        "@context": "https://doi.org/10.5063/schema/codemeta-2.0", "@type": "SoftwareSourceCode",
        "name": d["software"]["name"], "codeRepository": d["software"]["repository"],
        "license": "https://spdx.org/licenses/" + d["software"].get("licence", "NOASSERTION"),
        "version": str(d["software"].get("version", "")), "programmingLanguage": "Python"}
    if dom == "pyrcel":
        meta["author"] = [{"@type": "Person", "givenName": "Daniel", "familyName": "Rothenberg"}]
    meta["websemantic:pinnedRevision"] = d["software"].get("commit", "")
    meta["websemantic:semanticPack"] = f"https://github.com/cyrilvoyant/websemantic/tree/main/packs/{dom}"
    return json.dumps(meta, ensure_ascii=False, indent=2) + "\n"


def contract_section(dom):
    full = (ROOT / "LLM-CONTRACT.md").read_text(encoding="utf-8")
    head = full.split("\n## ", 2)
    rules = "## " + head[1].split("\n## ")[0] if len(head) > 1 else ""
    title = {"tls": "## Tunnel Load Simulator", "lqlequiv": "## LQL-Equiv", "pyrcel": "## pyrcel"}[dom]
    start = full.index(title)
    nxt = re.search(r"\n## ", full[start + 3:])
    sec = full[start: start + 3 + nxt.start()] if nxt else full[start:]
    return ("# LLM contract — read this file first\n\nPlace this pack next to the original code. Files: variables.csv, units.csv, "
            "outputs.csv, ontology.ttl, shapes.ttl, codemeta.json.\n\n" + rules.strip() + "\n\n" + sec.strip() + "\n")


FAIR = """# FAIR and FAIR4RS coverage of this pack

| Principle | Software (FAIR4RS) | Data produced (FAIR) |
|---|---|---|
| Findable | `codemeta.json`: name, repository, licence, pinned revision, link to this pack | `variables.csv` and `outputs.csv`: stable names linked to ontology concepts |
| Accessible | original repository URL and pinned revision; pack readable without any account | outputs written as CSV + JSON manifest; units and meanings in plain files |
| Interoperable | `ontology.ttl` (OWL, PROV-O, SKOS, QUDT alignment) and `shapes.ttl` (SHACL) | every unit and quantity kind as a QUDT IRI (`units.csv`); exact conversions declared |
| Reusable | `LLM-CONTRACT.md`: task scope, refusal rules, acceptance of assumptions | defaults and qualitative conventions with their authority; aggregation, temporal support and validity flags of each output |

References: Wilkinson et al., Scientific Data 3, 160018 (2016); Barker et al., Scientific Data 9, 622 (2022).
"""


def main():
    for dom in DOMAINS:
        d = descriptor(dom)
        out = ROOT / "packs" / dom
        out.mkdir(parents=True, exist_ok=True)
        (out / "LLM-CONTRACT.md").write_text(contract_section(dom), encoding="utf-8")
        (out / "variables.csv").write_text(variables_csv(dom, d), encoding="utf-8")
        (out / "units.csv").write_text(units_csv(d), encoding="utf-8")
        (out / "outputs.csv").write_text(outputs_csv(dom, d), encoding="utf-8")
        ttl = (ROOT / "ontology/core.ttl").read_text(encoding="utf-8") + "\n\n# ---- domain extension ----\n" + \
            (ROOT / "ontology" / EXT_TTL[dom]).read_text(encoding="utf-8")
        (out / "ontology.ttl").write_text(ttl, encoding="utf-8")
        (out / "shapes.ttl").write_text((ROOT / "ontology/shapes.ttl").read_text(encoding="utf-8"), encoding="utf-8")
        (out / "codemeta.json").write_text(codemeta(dom, d), encoding="utf-8")
        (out / "FAIR.md").write_text(FAIR, encoding="utf-8")
        print(dom, "pack written:", ", ".join(sorted(p.name for p in out.iterdir())))


if __name__ == "__main__":
    main()
