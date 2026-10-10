"""Build the files of the static web app (webapp/): the workspace bundle loaded by Pyodide in the visitor's browser,
and the per-code reading context fetched by the language-model relay (contract, tasks, parameters).

The bundle holds only what the two browser codes need: the websemantic package, the TLS and LQL-Equiv descriptors,
the ontology, the two examples and the pinned backends (TLS simulator, LQL-Equiv library) with their licences.
Usage: python tools/build_webapp.py
"""

import json
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


def bundle():
    files = []
    for folder, patterns in INCLUDE:
        for pattern in patterns:
            files += [p for p in (ROOT / folder).rglob(pattern) if "__pycache__" not in p.parts]
    files += [ROOT / s for s in SINGLE]
    target = OUT / "bundle.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(set(files)):
            z.writestr(path.relative_to(ROOT).as_posix(), path.read_bytes().replace(b"\r\n", b"\n"))
    print(f"{target.relative_to(ROOT)}: {len(set(files))} files, {target.stat().st_size / 1024:.0f} kB")


def reading_context():
    (OUT / "llm").mkdir(exist_ok=True)
    for code, (folder, pack) in CODES.items():
        desc = yaml.safe_load((ROOT / "descriptors" / folder / "descriptor.yaml").read_text(encoding="utf-8"))
        params = [{"field": n, "type": s.get("type"), "unit": s.get("unit"), "default": s.get("default"),
                   "label": s.get("label"), "categories": s.get("categories"),
                   "declared_levels": declared_levels(s) or None}
                  for g in ("inputs", "experiment") for n, s in (desc.get(g) or {}).items()]
        doc = {"code": code, "tasks": desc["tasks"]["supported"], "params": params,
               "contract": (ROOT / "packs" / pack / "LLM-CONTRACT.md").read_text(encoding="utf-8")}
        path = OUT / "llm" / f"{code}.json"
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
        print(f"{path.relative_to(ROOT)}: {len(params)} parameters")


if __name__ == "__main__":
    bundle()
    reading_context()
