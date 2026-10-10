"""Build the files of the static web app (webapp/): the workspace bundle loaded by Pyodide in the visitor's browser,
and the per-code reading context fetched by the language-model relay (contract, tasks, parameters).

The bundle holds only what the two browser codes need: the websemantic package, the TLS and LQL-Equiv descriptors,
the ontology, the two examples and the pinned backends (TLS simulator, LQL-Equiv library) with their licences.
Usage: python tools/build_webapp.py
"""

import json
import sys
import zipfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "webapp"
INCLUDE = [
    ("src/websemantic", ("*.py", "*.json")),
    ("descriptors/tls", ("*.yaml",)),
    ("descriptors/lqlequiv", ("*.yaml",)),
    ("ontology", ("*.ttl", "*.json")),
    ("external/tunnel-load-simulator/src/tunnel_load_simulator", ("*.py",)),
    ("external/LQL-Equiv-web/src/lqlequiv", ("*.py", "*.json", "*.csv")),
]
SINGLE = ["LICENSE", "examples/tls-complete.json", "examples/lql-complete.json",
          "external/tunnel-load-simulator/LICENSE", "external/LQL-Equiv-web/LICENSE"]
CODES = {"tls": ("tls", "tls"), "lql": ("lqlequiv", "lqlequiv")}  # id -> (descriptor folder, pack)


def declared_levels(spec):
    scale = spec.get("qualitative_scale") or {}
    out = {}
    for label, level in (scale.get("levels") or {}).items():
        value = level["value"] if "value" in level else scale.get("reference_upper", 0) * level.get("fraction", 0)
        out[label] = {"value": int(value) if spec.get("type") == "int" else float(value),
                      "expressions": level.get("aliases", [])}
    return out


def entries():
    """Published path -> LF-normalised bytes, for every file of the bundle (also used by the consistency test)."""
    files = []
    for folder, patterns in INCLUDE:
        for pattern in patterns:
            files += [p for p in (ROOT / folder).rglob(pattern) if "__pycache__" not in p.parts]
    files += [ROOT / s for s in SINGLE]
    return {p.relative_to(ROOT).as_posix(): p.read_bytes().replace(b"\r\n", b"\n") for p in sorted(set(files))}


def bundle():
    content = entries()
    target = OUT / "bundle.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in content.items():
            z.writestr(name, data)
    print(f"{target.relative_to(ROOT)}: {len(content)} files, {target.stat().st_size / 1024:.0f} kB")


def library_names(desc):
    """Organ and tumour-site names of the pinned LQL-Equiv library (sha256-checked loader), unchanged."""
    sys.path.insert(0, str(ROOT / "src"))
    from websemantic.adapters.lql import _backend
    library = _backend(ROOT, desc).load_library()
    return {"organ": list(library.organ_names), "tumour_site": list(library.tumour_names)}


def ontology_names():
    """Names of the LQL organs and tumour sites in the ontology (skos:altLabel), to help the reading model."""
    sys.path.insert(0, str(ROOT / "src"))
    from websemantic.lql_workbench import names
    return names(ROOT)


def reading_context():
    (OUT / "llm").mkdir(exist_ok=True)
    for code, (folder, pack) in CODES.items():
        desc = yaml.safe_load((ROOT / "descriptors" / folder / "descriptor.yaml").read_text(encoding="utf-8"))
        names = library_names(desc) if code == "lql" else {}
        semantic = ontology_names() if code == "lql" else {}
        params = [{"field": n, "type": s.get("type"), "unit": s.get("unit"),
                   "unit_names": [str(a) for a in s.get("unit_aliases") or [] if a and not str(a).isdigit()] or None,
                   "default": s.get("default"), "label": s.get("label"), "definition": s.get("definition"),
                   "categories": s.get("categories") or names.get(n),
                   "category_names": semantic.get(n) or None,  # French and common names, from the ontology
                   "declared_levels": declared_levels(s) or None}
                  for g in ("inputs", "experiment") for n, s in (desc.get(g) or {}).items()]
        if code == "lql":  # anatomical groups of organs, from the ontology (for "all organs at risk")
            from websemantic.lql_workbench import anatomy
            for p in params:
                if p["field"] == "organ":
                    p["anatomical_groups"] = {g["label"]: g["organs"] for g in anatomy(ROOT).values()}
        doc = {"code": code, "tasks": desc["tasks"]["supported"], "params": params,
               "contract": (ROOT / "packs" / pack / "LLM-CONTRACT.md").read_text(encoding="utf-8")}
        path = OUT / "llm" / f"{code}.json"
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
        print(f"{path.relative_to(ROOT)}: {len(params)} parameters")


if __name__ == "__main__":
    bundle()
    reading_context()
