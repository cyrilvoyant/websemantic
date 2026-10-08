"""Offline E3 preparation and evidence scoring; never contacts a provider.

Inputs and observations belong in the private benchmark reserve, not Git.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
from urllib.parse import urlsplit

VERSION = "e3-evidence-1.0"
FAIR_NAMES = {"CITATION.cff", "codemeta.json", ".zenodo.json"}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def local_file(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError(f"Missing or unsafe file: {relative}")
    return path


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def prepare(config, output):
    """Freeze selected files; candidate order must be supplied, not chosen afterwards."""
    if output.exists():
        raise ValueError("Output already exists; preserve the registered snapshot")
    if not config.get("cases") or not config.get("candidates"):
        raise ValueError("Cases and candidates must be registered")
    ids = [c["id"] for c in config["candidates"]]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate candidate identifiers")
    manifest = {"version": VERSION, "registration": config, "files": []}
    for candidate in config["candidates"]:
        cid = candidate["id"]
        if not cid.isalnum():
            raise ValueError("Use anonymous alphanumeric candidate identifiers")
        root = Path(candidate["root"]).resolve()
        scientific = candidate["scientific_files"]
        if not scientific:
            raise ValueError("A scientific baseline is required")
        fair = candidate.get("fair_files", [])
        if set(scientific) & set(fair):
            raise ValueError("Scientific and FAIR file sets must be disjoint")
        if any(Path(f).name not in FAIR_NAMES for f in fair):
            raise ValueError("FAIR intervention only accepts citation/CodeMeta/Zenodo metadata")
        for condition in ("fair0", "fair1"):
            for relative in scientific + (fair if condition == "fair1" else []):
                source = local_file(root, relative)
                target = output / condition / cid / relative
                if not target.resolve().is_relative_to(output.resolve()):
                    raise ValueError("Unsafe target")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(source.read_bytes())
                manifest["files"].append({"condition": condition, "candidate": cid,
                                          "path": relative, "sha256": digest(target),
                                          "role": "scientific" if relative in scientific else "fair"})
    # Shared scientific bytes make FAIR a separate intervention from O or C.
    write_json(output / "manifest.json", manifest)
    prompts = []
    for case in config["cases"]:
        for entry in ("no_links", "two_links"):
            prompt = case["request"]
            if entry == "two_links":
                prompt += "\nSources disponibles : " + case["official_url"] + " ; " + case["websemantic_url"]
            prompts.append({"case_id": case["id"], "mode": "open_web", "entry_assignment": entry,
                            "fair_assignment": "uncontrolled", "prompt": prompt})
        for fair_condition in ("fair0", "fair1"):
            prompts.append({"case_id": case["id"], "mode": "controlled_files",
                            "entry_assignment": "candidate_files", "fair_assignment": fair_condition,
                            "candidate_order": ids, "prompt": case["request"]})
    write_json(output / "prompts.json", prompts)
    return manifest


def source_category(url, case):
    """Match repository path boundaries, not a mention of 'websemantic' in text."""
    parsed = urlsplit(url)
    if parsed.scheme != "https":
        return "other"
    for label, key in (("official", "official_url"), ("websemantic", "websemantic_url")):
        ref = urlsplit(case[key])
        prefix = ref.path.rstrip("/")
        path = parsed.path.rstrip("/")
        if parsed.netloc == ref.netloc and (path == prefix or path.startswith(prefix + "/")):
            return label
        # raw.githubusercontent.com/owner/repo/revision/file
        if (ref.netloc == "github.com" and parsed.netloc == "raw.githubusercontent.com"
                and path.startswith(prefix + "/")):
            return label
    return "other"


def verified_artifact(root, record):
    try:
        return digest(local_file(root, record["path"])) == record["sha256"]
    except (KeyError, ValueError, OSError):
        return False


def supported_reading(root, evidence, response):
    if not verified_artifact(root, evidence.get("capture", {})):
        return False
    source = local_file(root, evidence["capture"]["path"]).read_text(encoding="utf-8")
    source_quote, response_quote = evidence.get("source_quote"), evidence.get("response_quote")
    return (evidence.get("annotation") == "supported" and isinstance(source_quote, str)
            and bool(source_quote) and source_quote in source and isinstance(response_quote, str)
            and bool(response_quote) and response_quote in response)


def numeric_score(expected, observed):
    """Compare only exact quantity, unit and support; unknown is never zero error."""
    rows = []
    for ref in expected:
        matches = [r for r in observed if (r.get("quantity"), r.get("unit"), r.get("support")) ==
                   (ref["quantity"], ref["unit"], ref["support"])]
        row = {"quantity": ref["quantity"], "unit": ref["unit"], "support": ref["support"],
               "status": "missing_or_ambiguous", "rmsd": None, "nRMSD_rms": None}
        if len(matches) == 1:
            a, b = ref["values"], matches[0].get("values", [])
            valid = (isinstance(a, list) and isinstance(b, list) and a and len(a) == len(b)
                     and all(isinstance(x, (int, float)) and not isinstance(x, bool)
                             and math.isfinite(x) for x in a + b))
            if valid:
                rmsd = math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)) / len(a))
                rms = math.sqrt(sum(x * x for x in a) / len(a))
                row.update(status="comparable", rmsd=rmsd,
                           nRMSD_rms=rmsd / rms if rms else None)
        rows.append(row)
    return rows


def score(observation, case, root):
    required = ("id", "case_id", "mode", "entry_assignment", "fair_assignment", "model",
                "tools", "fresh_session", "time_utc", "response_artifact")
    if any(k not in observation for k in required):
        raise ValueError("Observation lacks session/assignment/provenance fields")
    if observation["case_id"] != case["id"]:
        raise ValueError("Observation and case differ")
    if observation["mode"] not in {"open_web", "controlled_files"}:
        raise ValueError("Unknown mode")
    if observation["mode"] == "open_web" and observation["fair_assignment"] != "uncontrolled":
        raise ValueError("Public web FAIR exposure cannot be assigned by this offline bench")
    if observation["mode"] == "open_web" and observation["entry_assignment"] not in {"no_links", "two_links"}:
        raise ValueError("Unknown open-web entry assignment")
    if observation["mode"] == "controlled_files" and observation["fair_assignment"] not in {"fair0", "fair1"}:
        raise ValueError("Controlled file condition must be registered")
    if observation["mode"] == "controlled_files" and observation["entry_assignment"] != "candidate_files":
        raise ValueError("Controlled mode presents candidate files")
    if not isinstance(observation["fresh_session"], bool):
        raise TypeError("fresh_session must be an observed boolean")
    if not verified_artifact(root, observation["response_artifact"]):
        raise ValueError("Raw response unavailable or hash mismatch")
    opened = []
    for source in observation.get("opened_sources", []):
        if verified_artifact(root, source.get("capture", {})):
            opened.append(source_category(source["url"], case))
    cited = [source_category(url, case) for url in observation.get("cited_sources", [])]
    # Observer annotation needs captured passages; no keyword creates retrieval proof.
    response = local_file(root, observation["response_artifact"]["path"]).read_text(encoding="utf-8")
    reading = sum(supported_reading(root, e, response)
                  for e in observation.get("reading_evidence", []))
    execution = observation.get("execution", {})
    proofs = execution.get("artifacts", [])
    kinds = {p.get("kind") for p in proofs if verified_artifact(root, p)}
    bundle = {"scenario", "manifest", "outputs", "execution_log"}.issubset(kinds)
    numerical = numeric_score(case.get("reference_outputs", []), observation.get("reported_outputs", []))
    return {"version": VERSION, "observation_id": observation["id"], "case_id": case["id"],
            "mode": observation["mode"], "entry_assignment": observation["entry_assignment"],
            "fair_assignment": observation["fair_assignment"],
            "fresh_session": observation["fresh_session"], "cited_categories": cited,
            "verified_opened_categories": opened,
            "observed_first_entry": opened[0] if opened else "unobserved",
            "supported_reading_annotations": reading,
            "execution_claimed": execution.get("claimed", False),
            "execution_bundle_verified": bundle,
            "numerical": numerical,
            "archived_bundle_and_numeric_match": bool(bundle and numerical and
                all(r["status"] == "comparable" and r["rmsd"] <= case.get("absolute_tolerance", 0)
                    for r in numerical))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare")
    prep.add_argument("config", type=Path)
    prep.add_argument("output", type=Path)
    scoring = commands.add_parser("score")
    scoring.add_argument("observation", type=Path)
    scoring.add_argument("case", type=Path)
    scoring.add_argument("artifact_root", type=Path)
    scoring.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(json.loads(args.config.read_text(encoding="utf-8")), args.output)
    else:
        result = score(json.loads(args.observation.read_text(encoding="utf-8")),
                       json.loads(args.case.read_text(encoding="utf-8")), args.artifact_root)
        write_json(args.output, result)


if __name__ == "__main__":
    main()
