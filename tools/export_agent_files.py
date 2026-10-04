"""Publish the minimal web-readable source set for TLS execution."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    "agent/run_tls.py", "src/websemantic/__init__.py",
    "src/websemantic/core/__init__.py", "src/websemantic/core/validation.py",
    "src/websemantic/adapters/__init__.py", "src/websemantic/adapters/tls.py",
    "src/websemantic/adapters/tls_outputs.py", "src/websemantic/semantics.py",
    "ontology/tls-contract.json", "examples/tls-complete.json", "LICENSE",
    "external/tunnel-load-simulator/src/tunnel_load_simulator/simulator.py",
    "external/tunnel-load-simulator/LICENSE",
]


def main():
    records = []
    commit = "748e053e129669cf3e896d381e3c0ac01c763edd"
    for name in FILES:
        relative = name.removeprefix("external/tunnel-load-simulator/")
        url = (f"https://raw.githubusercontent.com/cyrilvoyant/tunnel-load-simulator/{commit}/{relative}"
               if name.startswith("external/") else
               f"https://raw.githubusercontent.com/cyrilvoyant/websemantic/main/{name}")
        data = (ROOT / name).read_bytes().replace(b"\r\n", b"\n")
        records.append({"path": name, "url": url,
                        "sha256_lf": hashlib.sha256(data).hexdigest()})
    document = {"schema_version": "websemantic-agent-files-1", "model": "tls",
                "dependencies": ["numpy", "pandas", "rdflib"],
                "backend_commit": commit, "files": records}
    (ROOT / "agent/files.json").write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
