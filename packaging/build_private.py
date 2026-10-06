"""Rebuild the local private distribution; never upload this archive."""

import zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
archive_path = root.parent / 'WebSemantic_TLS-test-prive.zip'
if not (root / '.env').is_file():
    raise SystemExit('Configuration privée absente.')
temporary = archive_path.with_suffix('.tmp.zip')
with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED) as new:
    # Ship source-only pinned backends, never Git metadata or an environment.
    for folder, license_name, source_name in (
        ('tunnel-load-simulator', 'LICENSE', 'src'),
        ('LQL-Equiv-web', 'LICENSE', 'src'),
        ('pyrcel', 'LICENSE.md', 'pyrcel'),
    ):
        backend = root / 'external' / folder
        source = backend / source_name
        if not source.is_dir() or not (backend / license_name).is_file():
            raise SystemExit('Backend incomplet : ' + folder)
        new.write(backend / license_name, 'WebSemantic_TLS/application/external/' + folder + '/' + license_name)
        for path in source.rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts and not path.name.endswith('.pyc'):
                new.write(path, 'WebSemantic_TLS/application/external/' + folder + '/' + path.relative_to(backend).as_posix())
    for directory in ('src', 'descriptors', 'ontology', 'docs', 'examples', 'tools', 'agent'):
        for path in (root / directory).rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts and not path.name.endswith('.pyc'):
                new.write(path, 'WebSemantic_TLS/application/' + path.relative_to(root).as_posix())
    for name in ('pyproject.toml', 'LICENSE', 'README.md', 'CITATION.cff', 'codemeta.json', 'AGENTS.md', '.env', 'installer-et-lancer.ps1', 'verifier-installation.py'):
        new.write(root / name, 'WebSemantic_TLS/application/' + name)
    for name in ('Installer.cmd', 'WebSemantic.cmd', 'Guide.txt'):
        new.write(root / 'packaging/windows' / name, 'WebSemantic_TLS/' + name)
temporary.replace(archive_path)
print('Archive privée mise à jour (aucune clé affichée).')
