"""Build the HPC archive from an allow-list, with a blocking secret scan and a SHA-256 manifest.

The archive contains the reserved corpus: it is private and must never be published.
"""

import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]          # ...\Documents\websemantic
ALLOW = {
    "semantic-sim-layer": ["src", "descriptors", "ontology", "packs", "evaluation", "examples", "external", "hpc", "tools",
                           "agent", "LLM-CONTRACT.md", "AGENTS.md", "llm.md", "pyproject.toml", "README.md", "LICENSE",
                           "CITATION.cff", "codemeta.json"],
    "benchmark-reserve": ["tls", "lqlequiv", "pyrcel", "knowledge-prior", "tools", "VALIDATION-pilote.md"],
}
SKIP_PARTS = {".git", "__pycache__", ".venv", "runs", "work", ".pytest_cache", ".ruff_cache"}
SKIP_FILE = re.compile(r"(^\.env)|(\.(pem|key|p12|pfx|zip|tgz)$)|(credential|secret)", re.IGNORECASE)
SECRET = re.compile(rb"AIza[0-9A-Za-z_-]{20,}|mstrl_[0-9A-Za-z_-]{10,}|sk-[0-9A-Za-z]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|"
                    rb"(GEMINI|MISTRAL|OPENAI|ANTHROPIC)_API_KEY\s*=\s*\S+")


def files():
    for top, entries in ALLOW.items():
        for entry in entries:
            p = ROOT / top / entry
            for f in ([p] if p.is_file() else p.rglob("*") if p.is_dir() else []):
                rel = f.relative_to(ROOT)
                if f.is_file() and not (set(rel.parts) & SKIP_PARTS) and not SKIP_FILE.search(f.name) and \
                        not (top == "semantic-sim-layer" and rel.parts[1:3] == ("evaluation", "e1") and f.name.startswith("e1-")):
                    yield f, rel


def main(out):
    manifest, hits = {}, []
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f, rel in files():
            data = f.read_bytes()
            if SECRET.search(data):
                hits.append(str(rel))
                continue
            manifest[str(rel).replace("\\", "/")] = hashlib.sha256(data).hexdigest()
            z.writestr(str(Path("websemantic") / rel).replace("\\", "/"), data)
        z.writestr("websemantic/MANIFEST.sha256.json", json.dumps(manifest, indent=1))
    if hits:
        Path(out).unlink()
        sys.exit("BLOCKED: possible secrets in " + ", ".join(hits))
    digest = hashlib.sha256(Path(out).read_bytes()).hexdigest()
    Path(str(out) + ".sha256").write_text(digest + "\n", encoding="utf-8")
    print(len(manifest), "files ->", out, "sha256", digest)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
