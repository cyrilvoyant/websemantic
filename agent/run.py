"""Execute an explicit accepted scientific scenario from published source files."""

import argparse
import hashlib
import importlib.metadata
import json
import platform
import sys
from dataclasses import asdict
from pathlib import Path


def verified_index(root, model):
    name = "files.json" if model == "tls" else f"files-{model}.json"
    index = json.loads((root / "agent" / name).read_text(encoding="utf-8"))
    if index["model"] != model:
        raise ValueError("Source index does not match the selected model.")
    for record in index["files"]:
        path = (root / record["path"]).resolve()
        if not path.is_relative_to(root):
            raise ValueError("Source path is outside the workspace.")
        actual = hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        if actual != record["sha256_lf"]:
            raise ValueError("Source incomplete or changed: " + record["path"])
    return index


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", choices=("tls", "lql", "pyrcel"))
    parser.add_argument("scenario", type=Path)
    parser.add_argument("--workspace", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--place")
    parser.add_argument("--context", type=Path)
    parser.add_argument("--previous", type=Path)
    args = parser.parse_args(argv)
    try:
        root = args.workspace.resolve()
        index = verified_index(root, args.model)
        # TLS retains its reviewed context, follow-up and comparison checks.
        if args.model == "tls":
            from run_tls import main as tls_main

            forwarded = [str(args.scenario), "--workspace", str(root)]
            for option in ("output_dir", "place", "context", "previous"):
                if getattr(args, option) is not None:
                    forwarded += ["--" + option.replace("_", "-"), str(getattr(args, option))]
            return tls_main(forwarded)
        if any(getattr(args, key) is not None for key in ("place", "context", "previous")):
            raise ValueError("Context/follow-up options are currently supported only by TLS.")
        sys.path.insert(0, str(root / "src"))
        from websemantic.core.validation import validate
        from websemantic.registry import execute, load_descriptor
        from websemantic.replay import load_scenario

        document = json.loads(args.scenario.read_text(encoding="utf-8"))
        scenario = load_scenario(document)
        descriptor = load_descriptor(root, args.model)
        if "software" in document and document["software"] != descriptor["software"]:
            raise ValueError("Saved software identity differs from the selected descriptor.")
        gate = validate(scenario, descriptor)
        if gate.decision != "execute":
            print(json.dumps(asdict(gate), ensure_ascii=False))
            return 2
        versions = {name: importlib.metadata.version(name) for name in index["dependencies"]}
        target, indicators = execute(scenario, descriptor, root, args.output_dir)
        manifest_path = target / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["source_materialization"] = {"method": "published_file_hashes", "files": index["files"]}
        manifest["execution_environment"] = {
            "python": platform.python_version(), "platform": platform.platform(),
            "packages": versions,
        }
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2,
                                            allow_nan=False), encoding="utf-8")
        print(json.dumps({"decision": "execute", "result_directory": str(target.resolve()),
                          "manifest": str(manifest_path.resolve()), "indicators": indicators},
                         ensure_ascii=False, allow_nan=False))
        return 0
    except (ImportError, KeyError, TypeError, ValueError, OSError) as error:
        print(json.dumps({"decision": "refuse", "error": str(error)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
