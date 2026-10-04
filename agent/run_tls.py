"""Execute an explicit TLS scenario from web-readable files, without Git or pip."""

import argparse
import hashlib
import json
import platform
import re
import sys
from dataclasses import asdict
from importlib.metadata import version
from pathlib import Path
from types import SimpleNamespace


def context_report(path, city):
    if not path:
        raise ValueError("Lieu cité : fournir --context avec sources consultées et hypothèses locales.")
    report = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(report, dict) or str(report.get("city", "")).casefold() != city.casefold():
        raise ValueError("Le contexte doit correspondre au lieu de l’étude.")
    if not isinstance(report.get("summary"), str) or not report["summary"].strip():
        raise ValueError("Résumé du contexte requis.")
    sources = report.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError("Tracer les sources consultées ou indisponibles.")
    for source in sources:
        if not isinstance(source, dict) or source.get("status") not in ("consulted", "unavailable"):
            raise ValueError("Statut de source invalide.")
        if not str(source.get("url", "")).startswith(("https://", "http://")) or not source.get("retrieved_at"):
            raise ValueError("URL et date de consultation requises.")
        if source["status"] == "consulted" and not source.get("evidence"):
            raise ValueError("Conserver l’élément documentaire utilisé.")
    for key in ("facts", "hypotheses"):
        if not isinstance(report.get(key), list) or any(not isinstance(v, str) for v in report[key]):
            raise ValueError("Distinguer faits et hypothèses dans le contexte.")
    if report["hypotheses"] and report.get("accepted") is not True:
        raise ValueError("Les hypothèses locales restent à accepter.")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", type=Path)
    parser.add_argument("--workspace", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--context", type=Path)
    parser.add_argument("--place")
    parser.add_argument("--previous", type=Path)
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
    def scenario_from(record):
        if set(record) != {"request", "task", "inputs", "experiment"}:
            raise ValueError("Expected request, task, inputs and experiment.")
        return Scenario(request=record["request"], task=record["task"],
                        inputs={k: Parameter(**v) for k, v in record["inputs"].items()},
                        experiment={k: Parameter(**v) for k, v in record["experiment"].items()})

    comparison = set(data) == {"scenario_1", "scenario_2"}
    scenarios = {key: scenario_from(record) for key, record in data.items()} if comparison else {"scenario": scenario_from(data)}
    from websemantic.units import fold

    cities = set()
    requests = " ".join(item.request for item in scenarios.values())
    for key, entry in contract.get("geography", {}).get("places", {}).items():
        if any(re.search(r"\b" + re.escape(alias) + r"\b", fold(requests))
               for alias in [fold(key), fold(entry["city"]), *map(fold, entry.get("aliases", []))]):
            cities.add(entry["city"])
    if args.place and not any(city.casefold() == args.place.casefold() for city in cities):
        cities.add(args.place)
    if len(cities) > 1:
        raise ValueError("Un seul contexte géographique par dossier ; séparer les études de lieux différents.")
    context = context_report(args.context, next(iter(cities))) if cities else None
    if args.context and not context:
        raise ValueError("Indiquer --place pour rattacher le contexte à l’étude.")
    if args.previous:
        previous = json.loads(args.previous.read_text(encoding="utf-8"))
        if comparison or "scenario" not in previous:
            raise ValueError("--previous attend une étude simple précédente.")
        changes = []
        for group in ("inputs", "experiment"):
            for name, record in data[group].items():
                old = previous["scenario"][group].get(name, {})
                if record.get("value") != old.get("value") or record.get("unit") != old.get("unit"):
                    changes.append({"field": group + "." + name, "before": old, "after": record})
        for name in ("n_runs", "base_seed", "freq_minutes"):
            old = previous["scenario"]["experiment"][name]
            new = data["experiment"][name]
            if old["value"] != new["value"] and new.get("origin") != "provided":
                raise ValueError("Conserver les réglages précédents sauf demande explicite : " + name)
    if comparison:
        from websemantic.comparison import run as compare

        sessions = {key: SimpleNamespace(scenario=scenario, pending_clarification=None,
                                        geographic_pending=False) for key, scenario in scenarios.items()}
        target, medians = compare(sessions, descriptor, root, args.output_dir)
    else:
        scenario = scenarios["scenario"]
        gate = validate(scenario, descriptor)
        if gate.decision != "execute":
            print(json.dumps(asdict(gate), ensure_ascii=False, indent=2))
            return 2
        target, medians = run(scenario, descriptor, root, args.output_dir)
    manifest_path = target / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if context:
        (target / "geographical_context.json").write_text(json.dumps(context, ensure_ascii=False, indent=2), encoding="utf-8")
        manifest["geographical_context"] = "geographical_context.json"
    if args.previous:
        manifest["previous_study"] = {"manifest": str(args.previous.resolve()), "changes": changes}
    manifest["execution_environment"] = {"python": platform.python_version(),
                                         "packages": {name: version(name) for name in index["dependencies"]}}
    manifest["source_materialization"] = {"method": "published_file_hashes", "files": index["files"]}
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"result_directory": str(target), "median_indicators": medians},
                     ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
