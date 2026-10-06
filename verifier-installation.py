"""Read-only checks shared by the launcher and installer. No installation calls."""

import argparse
import importlib
import importlib.metadata
import json
import math
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

REQUIRED = {
    'pydantic': ('2.6', 'pydantic'),
    'pyyaml': ('6.0', 'yaml'),
    'rdflib': ('7.0', 'rdflib'),
    'pyshacl': ('0.26', 'pyshacl'),
    'numpy': ('1.24', 'numpy'),
    'pandas': ('2.0', 'pandas'),
}
ATMOSPHERE = {
    'jax': ('0.11.2', 'jax'),
    'diffrax': ('0.7.2', 'diffrax'),
    'equinox': ('0.13.8', 'equinox'),
    'optimistix': ('0.1.0', 'optimistix'),
    'scipy': ('1.0', 'scipy'),
    'polars': ('1.0', 'polars'),
    'xarray': ('2024.1', 'xarray'),
    'netcdf4': ('1.0', 'netCDF4'),
}


def dependencies(include_atmosphere=False):
    problems = []
    if include_atmosphere and sys.version_info < (3, 12):
        return ['Python 3.12 ou supérieur est nécessaire pour les trois profils. Relancez Installer.cmd.']
    if sys.version_info < (3, 10):  # noqa: UP036 -- bootstrap may run before supported Python is installed
        return ['Python 3.10 ou supérieur est nécessaire.']
    try:
        from packaging.version import Version
    except ImportError:
        return ['Le composant de vérification des versions (packaging) est absent.']
    for name, (minimum, module) in (REQUIRED | ATMOSPHERE if include_atmosphere else REQUIRED).items():
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
    problems = dependencies(include_atmosphere=True)
    if problems:
        return problems
    try:
        import hashlib

        from websemantic.adapters.lql import EXPECTED_FILES
        from websemantic.adapters.pyrcel import verify_source
        tls = root / 'external/tunnel-load-simulator/src/tunnel_load_simulator/simulator.py'
        digest = hashlib.sha256(tls.read_bytes().replace(b'\r\n', b'\n')).hexdigest()
        if digest != '8377b8a26e18d060a7a217721100512625f53fbd4d8aa9d7a3b085bd14663464':
            return ['Les sources TLS ne correspondent pas à la version attendue.']
        for name, expected in EXPECTED_FILES.items():
            path = root / 'external/LQL-Equiv-web/src/lqlequiv' / name
            if hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest() != expected:
                return ['Les sources LQL ne correspondent pas à la version attendue.']
        verify_source(root / 'external/pyrcel')
    except (OSError, ValueError):
        return ['Sources absentes ou modifiées. Relancez Installer.cmd avec le package complet.']
    return []




def smoke(root):
    """Run the installed TLS adapter on one fictitious day; no LLM or saved study."""
    try:
        from websemantic.adapters.tls import run
        from websemantic.core.validation import Parameter, Scenario
        from websemantic.registry import load_descriptor

        descriptor = load_descriptor(root, "tls")
        records = {group: {name: Parameter(value=spec["default"], unit=spec.get("unit"),
                    origin="assumption", source="Fictitious installation check", accepted=True)
                    for name, spec in descriptor[group].items()} for group in ("inputs", "experiment")}
        for name, value in {"n_days": 1, "freq_minutes": 60, "n_runs": 1}.items():
            records["experiment"][name] = Parameter(value=value, unit=descriptor["experiment"][name].get("unit"),
                origin="assumption", source="Fictitious installation check", accepted=True)
        scenario = Scenario(request="Fictitious installation check", task=descriptor["tasks"]["supported"][0], **records)
        with TemporaryDirectory(prefix="websemantic-check-") as temporary:
            target, medians = run(scenario, descriptor, root, temporary)
            manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
            assert manifest["output_qualification"]["tables"]["representative"]["rows"] == 24
            assert manifest["output_qualification"]["tables"]["kpis"]["rows"] == 1
            assert all(math.isfinite(value) for value in medians.values())
            assert medians["total_mwh"] > 0
            assert all((target / (name + ".csv")).is_file() for name in manifest["outputs"])
            assert (target / "semantics.ttl").is_file()
    except (ImportError, OSError, ValueError, KeyError, TypeError, AssertionError,
            subprocess.SubprocessError, RuntimeError, ArithmeticError) as error:
        return ["Le test de calcul TLS a échoué : " + type(error).__name__ + "."]
    return []

def smoke_transfers(root):
    """Execute the two bounded transfer examples without loading an LLM key."""
    try:
        from dataclasses import replace

        from websemantic.registry import execute, load_descriptor
        from websemantic.replay import load_scenario
        with TemporaryDirectory(prefix='websemantic-transfer-check-') as temporary:
            for model, name in [('lql','lql-complete.json'), ('pyrcel','pyrcel-complete.json')]:
                descriptor = load_descriptor(root, model)
                scenario = load_scenario(json.loads((root / 'examples' / name).read_text(encoding='utf-8')))
                if model == 'pyrcel':
                    experiment = dict(scenario.experiment)
                    for field, value in [('t_end',30),('output_dt',5),('terminate','no')]:
                        experiment[field] = replace(experiment[field],value=value)
                    scenario = replace(scenario,experiment=experiment)
                target, indicators = execute(scenario, descriptor, root, temporary)
                assert (target / 'manifest.json').is_file() and (target / 'semantics.ttl').is_file()
                assert all(value is None or math.isfinite(value) for value in indicators.values())
    except (ImportError, OSError, ValueError, KeyError, TypeError, AssertionError, RuntimeError) as error:
        return ['Test de calcul de transfert échoué : ' + type(error).__name__ + '.']
    return []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dependencies-only', action='store_true')
    parser.add_argument('--smoke', action='store_true')
    args = parser.parse_args()
    problems = dependencies(include_atmosphere=True) if args.dependencies_only else runtime(Path(__file__).resolve().parent)
    if not problems and args.smoke:
        root = Path(__file__).resolve().parent
        problems = smoke(root)
        if not problems:
            problems = smoke_transfers(root)
        if not problems:
            print('Tests TLS, LQL et pyrcel réussis ; fichiers et unités vérifiés.')
    if problems:
        for problem in problems:
            print(problem)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
