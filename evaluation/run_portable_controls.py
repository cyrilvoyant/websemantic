"""Development controls of published-file execution; no language-model requests."""

import argparse
import copy
import hashlib
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.output = args.output.resolve()
    args.python = args.python.resolve()
    args.output.mkdir(parents=True, exist_ok=False)
    report = {"scope": "Constructed development controls, not an agent benchmark or independent environment replication",
              "created_at": datetime.now(timezone.utc).isoformat(), "models": []}
    for model, field in (("tls", "length_m"), ("lql", "dose_per_fraction"), ("pyrcel", "V")):
        index_name = "files.json" if model == "tls" else f"files-{model}.json"
        index = json.loads((ROOT / "agent" / index_name).read_text(encoding="utf-8"))
        root = args.output / model / "sources"
        for record in index["files"]:
            dest = root / record["path"]
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / record["path"], dest)
        shutil.copyfile(ROOT / "agent" / index_name, root / "agent" / index_name)
        assert not any(root.rglob(".git"))
        document = json.loads((root / f"examples/{model}-complete.json").read_text(encoding="utf-8"))
        if model == "tls":
            for name, value in (("n_days", 7), ("freq_minutes", 60), ("n_runs", 3)):
                document["experiment"][name]["value"] = value
        if model == "pyrcel":
            document["inputs"]["bins"]["value"] = 10
            for name, value in (("t_end", 30), ("output_dt", 5), ("terminate", "no")):
                document["experiment"][name]["value"] = value
        row = {"model": model, "index_sha256": digest(root / "agent" / index_name),
               "positive": [], "negative": [], "repeat": []}

        def invoke(label, scenario, model=model, root=root):
            case = args.output / model / label
            case.mkdir()
            path = case / "scenario.json"
            path.write_text(json.dumps(scenario, ensure_ascii=False, indent=2), encoding="utf-8")
            env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "GEMINI_API_KEY")}
            env["PYTHONIOENCODING"] = "utf-8"
            process = subprocess.run([str(args.python.resolve()), str(root / "agent/run.py"), model,
                                      str(path.resolve()), "--output-dir", str((case / "runs").resolve())],
                                     capture_output=True, text=True, encoding="utf-8", errors="replace",
                                     env=env, cwd=case, timeout=180, check=False)
            (case / "stdout.txt").write_text(process.stdout, encoding="utf-8")
            (case / "stderr.txt").write_text(process.stderr, encoding="utf-8")
            result = json.loads(process.stdout)
            return {"label": label, "returncode": process.returncode, "response": result,
                    "output_created": (case / "runs").exists()}

        for repetition in range(2):
            result = invoke(f"accepted-{repetition+1}", document)
            assert result["returncode"] == 0, result
            target = Path(result["response"]["result_directory"])
            manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
            saved = manifest["scenario"]
            assert saved["request"] == document["request"] and saved["task"] == document["task"]
            for group in ("inputs", "experiment"):
                assert set(saved[group]) == set(document[group])
                for name, record in document[group].items():
                    assert all(saved[group][name][key] == value for key, value in record.items())
            assert manifest["source_materialization"]["files"] == index["files"]
            assert (target / "semantics.ttl").is_file()
            tables = manifest["output_qualification"]["tables"]
            result["qualified_tables"] = len(tables)
            result["qualified_columns"] = 0
            for table in tables.values():
                columns = pd.read_csv(target / table["file"]).columns
                assert set(columns) <= set(table["columns"]), (model, table["file"], columns)
                for column in columns:
                    metadata = table["columns"][column]
                    assert "unit" in metadata and metadata.get("meaning"), (model, column, metadata)
                    result["qualified_columns"] += 1
            result["artifacts"] = {p.name: digest(p) for p in target.iterdir() if p.is_file()}
            row["positive"].append(result)
        first, second = [Path(r["response"]["result_directory"]) for r in row["positive"]]
        for csv_path in first.glob("*.csv"):
            a, b = pd.read_csv(csv_path), pd.read_csv(second / csv_path.name)
            assert list(a.columns) == list(b.columns) and a.shape == b.shape
            for column in a:
                if pd.api.types.is_numeric_dtype(a[column]) and pd.api.types.is_numeric_dtype(b[column]):
                    assert a[column].isna().equals(b[column].isna())
                    mask = a[column].notna()
                    x, y = a.loc[mask, column].to_numpy(), b.loc[mask, column].to_numpy()
                    error = float(np.sqrt(np.mean((x.astype(float)-y.astype(float))**2))) if len(x) else None
                    denom = float(np.sqrt(np.mean(y.astype(float)**2))) if len(y) else 0
                    row["repeat"].append({"table": csv_path.name, "column": column, "n": len(x),
                                          "rmsd": error, "nrmsd": error/denom if denom else None})
                else:
                    assert a[column].equals(b[column]), (model, column)
        for label in ("wrong-unit", "unaccepted", "acceptance-as-text", "missing-field",
                      "changed-definition", "changed-backend"):
            invalid = copy.deepcopy(document)
            changed = None
            if label == "wrong-unit":
                invalid["inputs"][field]["unit"] = "unit:KG"
            elif label == "unaccepted":
                invalid["inputs"][field]["accepted"] = False
            elif label == "acceptance-as-text":
                invalid["inputs"][field]["accepted"] = "false"
            elif label == "missing-field":
                del invalid["inputs"][field]
            else:
                selected = ("ontology/tls-contract.json" if model == "tls" else
                            f"descriptors/{'lqlequiv' if model == 'lql' else model}/descriptor.yaml")
                if label == "changed-backend":
                    selected = next(r["path"] for r in index["files"]
                                    if r["path"].startswith("external/") and r["path"].endswith(".py"))
                changed = root / selected
                original = changed.read_bytes()
                changed.write_bytes(original + b"\n# development perturbation\n")
            try:
                result = invoke(label, invalid)
            finally:
                if changed:
                    changed.write_bytes(original)
            assert result["returncode"] != 0 and not result["output_created"], result
            row["negative"].append(result)
        report["models"].append(row)
        print(model, "two runs and six blocked perturbations", flush=True)
        (args.output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2,
                                                           allow_nan=False), encoding="utf-8")


if __name__ == "__main__":
    main()
