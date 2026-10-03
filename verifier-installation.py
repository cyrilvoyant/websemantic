"""Read-only checks shared by the launcher and installer. No installation calls."""

import argparse
import importlib
import importlib.metadata
import shutil
import subprocess
import sys
from pathlib import Path

REQUIRED = {
    'pydantic': ('2.6', 'pydantic'),
    'pyyaml': ('6.0', 'yaml'),
    'rdflib': ('7.0', 'rdflib'),
    'pyshacl': ('0.26', 'pyshacl'),
    'numpy': ('1.24', 'numpy'),
    'pandas': ('2.0', 'pandas'),
}


def dependencies():
    problems = []
    if sys.version_info < (3, 10):  # noqa: UP036 -- bootstrap may run before supported Python is installed
        return ['Python 3.10 ou supérieur est nécessaire.']
    try:
        from packaging.version import Version
    except ImportError:
        return ['Le composant de vérification des versions (packaging) est absent.']
    for name, (minimum, module) in REQUIRED.items():
        try:
            installed = importlib.metadata.version(name)
            if Version(installed) < Version(minimum):
                problems.append(f'{name} {installed} : version {minimum} ou supérieure nécessaire.')
                continue
            importlib.import_module(module)
        except importlib.metadata.PackageNotFoundError:
            problems.append(f'Le composant {name} est absent (minimum {minimum}).')
        except (ImportError, OSError, ValueError):
            problems.append(f'Le composant {name} est présent mais inutilisable.')
    try:
        importlib.metadata.version('websemantic')
        importlib.import_module('websemantic.cli')
    except (ImportError, OSError, ValueError):
        problems.append('WebSemantic_TLS est absent ou son installation est incomplète.')
    return problems


def runtime(root):
    problems = dependencies()
    if problems:
        return problems
    git = shutil.which('git')
    if not git:
        return ['Git est introuvable : il est nécessaire pour vérifier la version du simulateur.']
    try:
        from websemantic.registry import environments, load_descriptor

        active = next(item for item in environments() if item['available'])
        descriptor = load_descriptor(root, active['id'])
        metadata = descriptor.get('runtime', {})
        if 'backend_path' not in metadata:
            return []
        backend = root / metadata['backend_path']
        marker = backend / metadata['backend_marker']
        if not marker.is_file():
            return ['Les fichiers du simulateur ou son descripteur sont absents.']
        expected = descriptor['software']['commit']
        commit = subprocess.check_output([git, '-C', str(backend), 'rev-parse', 'HEAD'], text=True, stderr=subprocess.DEVNULL, timeout=10).strip()
        dirty = subprocess.check_output([git, '-C', str(backend), 'status', '--porcelain', '--untracked-files=no'], text=True, stderr=subprocess.DEVNULL, timeout=10)
        if commit != expected or dirty:
            return ['Le simulateur ne correspond pas à la version de recherche prévue, ou ses sources ont été modifiées.']
    except FileNotFoundError:
        return ["Les fichiers du simulateur ou son descripteur sont absents."]
    except (OSError, subprocess.SubprocessError, KeyError, ValueError, TypeError, StopIteration):
        return ['La vérification du simulateur est impossible.']
    return []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dependencies-only', action='store_true')
    args = parser.parse_args()
    problems = dependencies() if args.dependencies_only else runtime(Path(__file__).resolve().parent)
    if problems:
        for problem in problems:
            print(problem)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
