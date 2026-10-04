"""Replay an explicit scenario or saved manifest without an LLM or implicit defaults."""

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from websemantic.core.validation import Parameter, Scenario, validate
from websemantic.registry import execute, load_descriptor


def load_scenario(document):
    if not isinstance(document, dict):
        raise TypeError("Scenario document must be a JSON object.")
    data = document.get("scenario", document)
    if not isinstance(data, dict):
        raise TypeError("Scenario must be a JSON object.")
    if set(data) != {"request", "task", "inputs", "experiment"}:
        raise ValueError("Scenario must contain exactly request, task, inputs and experiment.")
    if not isinstance(data["request"], str) or not isinstance(data["task"], str):
        raise TypeError("Request and task must be strings.")
    for group in ("inputs", "experiment"):
        if not isinstance(data[group], dict):
            raise TypeError("Parameter groups must be JSON objects.")
        for record in data[group].values():
            if not isinstance(record, dict):
                raise TypeError("Parameter records must be JSON objects.")
            for key in ("source", "evidence", "unit"):
                if record.get(key) is not None and not isinstance(record[key], str):
                    raise TypeError(f"{key} must be a string or null.")
            if "accepted" in record and type(record["accepted"]) is not bool:
                raise TypeError("Acceptance must be a JSON boolean.")
    return Scenario(
        request=data["request"], task=data["task"],
        inputs={name: Parameter(**record) for name, record in data["inputs"].items()},
        experiment={name: Parameter(**record) for name, record in data["experiment"].items()},
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", type=Path)
    parser.add_argument("--model", required=True)
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)
    try:
        document = json.loads(args.scenario.read_text(encoding="utf-8"))
        scenario = load_scenario(document)
        descriptor = load_descriptor(args.workspace, args.model)
        if "software" in document and document["software"] != descriptor["software"]:
            raise ValueError("Saved software identity differs from the current descriptor; replay refused.")
        gate = validate(scenario, descriptor)
        if gate.decision != "execute":
            print(json.dumps(asdict(gate), ensure_ascii=False, indent=2))
            return 2
        target, medians = execute(scenario, descriptor, args.workspace, args.output_dir)
        print(json.dumps({"decision": "execute", "result_directory": str(target.resolve()),
                          "manifest": str((target / "manifest.json").resolve()),
                          "median_indicators": medians}, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except (KeyError, TypeError, ValueError, OSError) as error:
        print(json.dumps({"decision": "refuse", "error": str(error)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
