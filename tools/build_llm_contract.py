"""Generate LLM-CONTRACT.md, the single mandatory entry point for language models, from the descriptors."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
NAMES = {"tls": "Tunnel Load Simulator (TLS)", "lqlequiv": "LQL-Equiv", "pyrcel": "pyrcel"}
REPOS = {"tls": "https://github.com/cyrilvoyant/tunnel-load-simulator",
         "lqlequiv": "https://github.com/cyrilvoyant/LQL-Equiv-web", "pyrcel": "https://github.com/darothen/pyrcel"}
OUT_OF_SCOPE = {"tls": "certification or prediction of a real tunnel's consumption",
                "lqlequiv": "any treatment decision for a patient", "pyrcel": "weather or cloud forecasts for a real place and time"}
CLARIFY = {
    "tls": "« fortement / faiblement éclairé » (TLS has no illuminance parameter); « ancien éclairage » (no category)",
    "lqlequiv": "« hypofractionnement modéré / extrême », « stéréotaxique », « hyperfractionnement », « dose élevée », « peu de séances »",
    "pyrcel": "« faible / forte ascendance », « air pur / marin / pollué / continental », « air presque saturé »",
}
RULES = """## Rules

1. **Never invent a value.** Each value is given in the request, an exact conversion of a given value (2 km → 2000 m), a declared default *proposed* to the user, or a declared qualitative convention *proposed* to the user.
2. **Defaults and qualitative conventions need explicit acceptance** before any calculation. « Prends les valeurs par défaut » accepts defaults; it does not accept a qualitative proposal, which needs its own agreement.
3. **Qualitative words have a meaning only through the tables below**, parameter by parameter. A word absent from the tables, or listed under *clarify*, has no numerical meaning: ask.
4. **Units**: use the canonical unit listed. Never mix a percentage and a fraction.
5. **Out of scope → refuse** (see each software).
6. **Conflicts** (two values for one quantity, a total that disagrees with its parts) are reported, never resolved silently.
7. Return the scenario as JSON: `decision` (execute | clarify | refuse), `values` [{field, value, unit, origin, evidence}], `questions`, and a plain three-sentence `restatement` (objective; retained values with units; what still needs acceptance).

Execution is done by the reviewed Python entry points (`agent/README.md`). Never present an unexecuted calculation as a result.
"""


def cell(x):
    return str(x).replace("|", "/").replace("\n", " ")


def section(dom):
    d = yaml.safe_load((ROOT / "descriptors" / dom / "descriptor.yaml").read_text(encoding="utf-8"))
    tasks = d.get("tasks", {})
    lines = [f"## {NAMES[dom]}", "", f"Original code: {REPOS[dom]} (pinned revision in `descriptors/{dom}/descriptor.yaml`).", "",
             f"Supported: {'; '.join(tasks.get('supported', []))}. Out of scope: {OUT_OF_SCOPE[dom]}.", "",
             "| Field | Unit or categories | Bounds | Default (proposal only) | Meaning |", "|---|---|---|---|---|"]
    quals = []
    for group in ("inputs", "experiment"):
        for name, s in (d.get(group) or {}).items():
            bounds = ", ".join(f"{k} {v}" for k, v in (s.get("bounds") or {}).items() if k != "authority")
            unit = s.get("unit") or ("categories: " + ", ".join(map(str, s["values"])) if s.get("values") else "")
            lines.append(f"| `{name}` | {cell(unit)} | {bounds} | {cell(s.get('default', ''))} | {cell(s.get('definition') or '')} |")
            scale = s.get("qualitative_scale") or {}
            for level, v in (scale.get("levels") or {}).items():
                expr = ", ".join(f"« {a} »" for a in v.get("aliases", [])) or level
                value = v.get("value")
                if value is None and "fraction" in v and "reference_upper" in scale:
                    value = round(v["fraction"] * scale["reference_upper"], 6)  # declared as a fraction of the upper reference
                if value is None:
                    raise ValueError(f"{dom}.{name}.{level}: no value or fraction")
                quals.append(f"| {expr} | `{name}` | {value} {s.get('unit') or ''} |")
    lines += ["", "**Qualitative conventions** (propose the value, then ask for acceptance):", ""]
    lines += (["| Expression | Field | Proposed value |", "|---|---|---|"] + quals) if quals else ["None declared."]
    lines += ["", f"**Clarify, never convert:** {CLARIFY[dom]}.", ""]
    # Optional, software-agnostic blocks: declared only by descriptors that need them.
    if d.get("qualitative_policy"):
        lines += [f"**Qualitative policy:** {cell(d['qualitative_policy'])}", ""]
    comp = d.get("comparison_task")
    if comp:
        lines += [f"**Task `{comp['task']}`** — {cell(comp['label'])}. Scope: {cell(comp['scope'])}.", "",
                  f"Criterion: {cell(comp['criterion'])}", "",
                  "Admissible decisions: " + "; ".join(cell(x) for x in comp.get("admissible_decisions", [])) + ".", ""]
    groups = d.get("anatomical_groups")
    if groups:
        lines += ["**Anatomical groups** (study convention over exact library names; a group never selects the organ at risk):", "",
                  "| Group | Expressions | Tumour sites | Organs |", "|---|---|---|---|"]
        for key, g in groups.items():
            lines.append(f"| `{key}` ({cell(g['label'])}) | {', '.join(f'« {a} »' for a in g.get('aliases', []))} | "
                         f"{cell(', '.join(g.get('tumour_sites', [])) or '—')} | {cell(', '.join(g.get('organs', [])))} |")
        lines.append("")
    return lines


def main():
    intro = ("Mandatory entry point for any language model configuring TLS, LQL-Equiv or pyrcel through WebSemantic. "
             "Generated by `tools/build_llm_contract.py` from `descriptors/`; if they disagree, the descriptors prevail.")
    out = ["# LLM contract — read this file first", "", intro, "", RULES]
    for dom in ("tls", "lqlequiv", "pyrcel"):
        out += section(dom)
    (ROOT / "LLM-CONTRACT.md").write_text("\n".join(out), encoding="utf-8")
    print(len("\n".join(out)), "chars")


if __name__ == "__main__":
    main()
