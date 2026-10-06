"""Test extracted private sources without loading the key or installing anything."""
import json
import math
import platform
import sys
import zipfile
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory


def main():
    repo = Path(__file__).resolve().parents[1]
    archive = repo.parent / 'WebSemantic_TLS-test-prive.zip'
    with TemporaryDirectory(prefix='websemantic-package-') as temporary:
        with zipfile.ZipFile(archive) as bundle:
            assert bundle.testzip() is None
            assert not any('/.git/' in n or '/.venv/' in n for n in bundle.namelist())
            bundle.extractall(temporary)
        root = Path(temporary) / 'WebSemantic_TLS/application'
        sys.path.insert(0, str(root / 'src'))
        import importlib.util

        from websemantic.core.validation import validate
        from websemantic.registry import execute, load_descriptor
        from websemantic.replay import load_scenario
        spec = importlib.util.spec_from_file_location('package_check', root / 'verifier-installation.py')
        check = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(check)
        assert check.runtime(root) == [], check.runtime(root)
        results = []
        for model, filename in [('tls','tls-complete.json'), ('lql','lql-complete.json'), ('pyrcel','pyrcel-complete.json')]:
            descriptor = load_descriptor(root, model)
            scenario = load_scenario(json.loads((root / 'examples' / filename).read_text(encoding='utf-8')))
            if model == 'pyrcel':
                experiment = dict(scenario.experiment)
                for name, value in [('t_end',30),('output_dt',5),('terminate','no')]:
                    experiment[name] = replace(experiment[name], value=value)
                scenario = replace(scenario, experiment=experiment)
            assert validate(scenario, descriptor).decision == 'execute'
            target, indicators = execute(scenario, descriptor, root, root / 'test-results')
            manifest = json.loads((target / 'manifest.json').read_text(encoding='utf-8'))
            assert (target / 'semantics.ttl').is_file()
            assert all(v is None or math.isfinite(v) for v in indicators.values())
            results.append({'model':model,'source_commit':manifest['software']['commit'],
                            'csv_count':len(list(target.glob('*.csv'))),'finite_or_qualified_null':True})
        report = {'scope':'Extracted private source package, existing dependency environment; no fresh Windows installation or Gemini call.',
                  'python':platform.python_version(),'system':platform.system(),'models':results}
        (repo / 'evaluation/package-smoke.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        print('Extracted package: TLS, LQL and pyrcel calculations and RDF verified; no key loaded.')


if __name__ == '__main__':
    main()
