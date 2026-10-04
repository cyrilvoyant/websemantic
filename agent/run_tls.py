"""Execute an explicit TLS scenario from web-readable files, without Git or pip."""

import argparse
import hashlib
import json
import platform
import sys
from dataclasses import asdict
from importlib.metadata import version
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", type=Path)
    parser.add_argument("--workspace", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)
    root = args.workspace.resolve()
    index = json.loads((root / "agent/files.json").read_text(encoding="utf-8"))
    for record in index["files"]:
        path = root / record["path"]
        data = path.read_bytes().replace(b"\r\n", b"\n")
        if hashlib.sha256(data).hexdigest() != record["sha256_lf"]:
            raise ValueError("Source incomplete or changed: " + record["path"])
    sys.path.insert(0, str(root / "src"))
    from websemantic.adapters.tls import run
    from websemantic.core.validation import Parameter, Scenario, validate

    contract = json.loads((root / "ontology/tls-contract.json").read_text(encoding="utf-8"))
    descriptor = {**contract, **contract["parameters"]}
    data = json.loads(args.scenario.read_text(encoding="utf-8"))
    if set(data) != {"request", "task", "inputs", "experiment"}:
        raise ValueError("Expected request, task, inputs and experiment.")
    scenario = Scenario(request=data["request"], task=data["task"],
                        inputs={k: Parameter(**v) for k, v in data["inputs"].items()},
                        experiment={k: Parameter(**v) for k, v in data["experiment"].items()})
    gate = validate(scenario, descriptor)
    if gate.decision != "execute":
        print(json.dumps(asdict(gate), ensure_ascii=False, indent=2))
        return 2
    target, medians = run(scenario, descriptor, root, args.output_dir)
    manifest_path = target / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["execution_environment"] = {"python": platform.python_version(),
                                         "packages": {name: version(name) for name in index["dependencies"]}}
    manifest["source_materialization"] = {"method": "published_file_hashes", "files": index["files"]}
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"result_directory": str(target), "median_indicators": medians},
                     ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
