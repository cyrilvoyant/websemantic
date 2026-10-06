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
    "src/websemantic/comparison.py", "src/websemantic/registry.py", "src/websemantic/units.py",
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


def export_transfer(model, folder, adapter, repository, commit, backend, license_name):
    names = ['src/websemantic/__init__.py', 'src/websemantic/core/__init__.py',
             'src/websemantic/core/validation.py', 'src/websemantic/adapters/__init__.py',
             'src/websemantic/replay.py', 'src/websemantic/registry.py', 'src/websemantic/environments.json', 'pyproject.toml',
             'src/websemantic/adapters/' + adapter + '.py', 'src/websemantic/semantics.py',
             'descriptors/' + folder + '/descriptor.yaml', 'examples/' + model + '-complete.json',
             'docs/' + model + '-contract-definitions.md', 'ontology/core.ttl',
             'ontology/' + folder + '.ttl', 'LICENSE', 'external/' + backend + '/' + license_name]
    source = ROOT / 'external' / backend
    selected = source / ('src/lqlequiv' if model == 'lql' else 'pyrcel')
    names += [p.relative_to(ROOT).as_posix() for p in selected.rglob('*')
              if p.is_file() and p.suffix in ('.py', '.json') and '__pycache__' not in p.parts]
    records = []
    prefix = 'external/' + backend + '/'
    for name in names:
        url = ('https://raw.githubusercontent.com/' + repository + '/' + commit + '/' + name.removeprefix(prefix)
               if name.startswith(prefix) else 'https://raw.githubusercontent.com/cyrilvoyant/websemantic/main/' + name)
        records.append({'path':name,'url':url,'sha256_lf':hashlib.sha256((ROOT/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()})
    document = {'model':model,'backend_commit':commit,'scope':'Reviewed bounded adapter; explicit accepted scenario; no Git required.',
                'files':records}
    (ROOT/'agent'/('files-' + model + '.json')).write_text(json.dumps(document,indent=2)+'\n',encoding='utf-8')


if __name__ == "__main__":
    main()
    export_transfer('lql','lqlequiv','lql','cyrilvoyant/LQL-Equiv-web',
                    'dfc9a338205b8864b8e3470c4ae245b019e88844','LQL-Equiv-web','LICENSE')
    export_transfer('pyrcel','pyrcel','pyrcel','darothen/pyrcel',
                    '977e9094644ec4a17d658d657094651928591c89','pyrcel','LICENSE.md')
