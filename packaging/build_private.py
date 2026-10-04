"""Rebuild the local private distribution; never upload this archive."""

import zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
archive_path = root.parent / 'WebSemantic_TLS-test-prive.zip'
if not archive_path.is_file() or not (root / '.env').is_file():
    raise SystemExit('Archive de référence ou configuration privée absente.')
temporary = archive_path.with_suffix('.tmp.zip')
with zipfile.ZipFile(archive_path) as old, zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED) as new:
    # Preserve only the pinned backend and its self-contained Git metadata.
    for item in old.infolist():
        if item.filename.startswith('WebSemantic_TLS/application/external/tunnel-load-simulator/'):
            new.writestr(item, old.read(item.filename))
    for directory in ('src', 'descriptors', 'ontology', 'docs', 'examples', 'tools'):
        for path in (root / directory).rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts and not path.name.endswith('.pyc'):
                new.write(path, 'WebSemantic_TLS/application/' + path.relative_to(root).as_posix())
    for name in ('pyproject.toml', 'LICENSE', 'README.md', 'CITATION.cff', 'codemeta.json', 'AGENTS.md', '.env', 'installer-et-lancer.ps1', 'verifier-installation.py'):
        new.write(root / name, 'WebSemantic_TLS/application/' + name)
    for name in ('Installer.cmd', 'WebSemantic.cmd', 'Guide.txt'):
        new.write(root / 'packaging/windows' / name, 'WebSemantic_TLS/' + name)
temporary.replace(archive_path)
print('Archive privée mise à jour (aucune clé affichée).')
