"""Validated fictitious schedule comparisons, using the unchanged LQL adapter."""

import csv
import json
import math
import re
import uuid
from dataclasses import asdict, replace
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

from websemantic.core.validation import Parameter, validate
from websemantic.registry import execute
from websemantic.replay import load_scenario


def verdict(left, right):
    """Compare two valid TCP/NTCP pairs; undefined probabilities forbid ranking."""
    keys = ("tcp_percent", "ntcp_percent")
    values = [item.get(key) for item in (left, right) for key in keys]
    if any(type(value) not in (int, float) or not math.isfinite(value)
           or not 0 <= value <= 100 for value in values):
        return {"verdict": "indeterminate", "delta_tcp_percent": None,
                "delta_ntcp_percent": None}
    dt = left[keys[0]] - right[keys[0]]
    dn = left[keys[1]] - right[keys[1]]
    result = "tradeoff"
    if dt == dn == 0:
        result = "equivalent"
    elif dt >= 0 and dn <= 0:
        result = "left_dominates"
    elif dt <= 0 and dn >= 0:
        result = "right_dominates"
    return {"verdict": result, "delta_tcp_percent": dt, "delta_ntcp_percent": dn}


def prepare(document, descriptor):
    """Expand explicitly accepted target selections and validate every native run."""
    if not isinstance(document, dict) or document.get("task") != "compare_schedules":
        raise ValueError("Expected a compare_schedules document.")
    if set(document) - {"task", "schedules", "targets", "anatomical_group"}:
        raise ValueError("Unknown comparison field.")
    schedules = document.get("schedules")
    if not isinstance(schedules, list) or len(schedules) < 2:
        raise ValueError("At least two explicit schedules are required.")
    entries = []
    for item in schedules:
        if not isinstance(item, dict) or set(item) != {"id", "scenario"}:
            raise ValueError("Each schedule requires id and scenario.")
        name = item["id"]
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", name):
            raise ValueError("Schedule identifiers use letters, numbers, _ or -.")
        scenario = load_scenario(item["scenario"])
        if scenario.task != "simulate fictitious radiobiological fractionation":
            raise ValueError("Each schedule must use the single fictitious course task.")
        entries.append((name, scenario))
    if len({name for name, _ in entries}) != len(entries):
        raise ValueError("Schedule identifiers must be unique.")
    reference = entries[0][1]
    for _, scenario in entries:
        for key in ("organ", "reference_dose"):
            if scenario.inputs.get(key) is None or reference.inputs.get(key) is None:
                raise ValueError(f"Explicit common {key} is required.")
            if scenario.inputs[key].value != reference.inputs[key].value:
                raise ValueError(f"Schedules must share {key}.")
    selection = [name for name in ("targets", "anatomical_group") if name in document]
    if len(selection) > 1:
        raise ValueError("Choose targets or anatomical_group, not both.")
    record = None
    if selection:
        record = Parameter(**document[selection[0]])
        if record.origin != "assumption" or record.accepted is not True or not record.source:
            raise ValueError("Target selection needs a source and explicit acceptance.")
        if record.unit is not None or record.conflicts:
            raise ValueError("Target selection must be unambiguous and unitless.")
        if selection[0] == "anatomical_group":
            group = descriptor.get("anatomical_groups", {}).get(record.value)
            if group is None:
                raise ValueError("Unknown anatomical group.")
            targets = group["tumour_sites"]
        else:
            targets = record.value
    else:
        targets = [reference.inputs.get("tumour_site", Parameter()).value]
        if any(scenario.inputs.get("tumour_site", Parameter()).value != targets[0]
               for _, scenario in entries):
            raise ValueError("Schedules must share a target, or declare targets explicitly.")
    if not isinstance(targets, list) or not targets or len(set(targets)) != len(targets):
        raise ValueError("A nonempty unique target list is required.")
    if any(target not in descriptor["inputs"]["tumour_site"]["values"] for target in targets):
        raise ValueError("Unknown target in library.")
    expanded = []
    for target in targets:
        for name, scenario in entries:
            if record is not None:
                scenario = replace(scenario, inputs={**scenario.inputs, "tumour_site":
                    replace(record, value=target)})
            gate = validate(scenario, descriptor)
            if gate.decision != "execute":
                raise ValueError(f"{name}/{target}: " + json.dumps(asdict(gate), ensure_ascii=False))
            expanded.append((name, target, scenario))
    return expanded


def run(document, descriptor, workspace, output_root=None):
    expanded = prepare(document, descriptor)  # all gates before the first calculation
    root = Path(output_root) if output_root else Path(workspace) / "runs"
    target = root / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                     + "-lql-comparison-" + uuid.uuid4().hex[:8])
    target.mkdir(parents=True)
    rows, runs, pairwise = [], [], []
    by_target = {}
    for index, (name, tissue, scenario) in enumerate(expanded):
        path, values = execute(scenario, descriptor, workspace, target / name / str(index))
        rows.append({"scenario": name, "target": tissue, **values})
        runs.append({"scenario": name, "target": tissue,
                     "directory": path.relative_to(target).as_posix()})
        by_target.setdefault(tissue, []).append((name, values))
    for tissue, entries in by_target.items():
        for (left, lv), (right, rv) in combinations(entries, 2):
            pairwise.append({"target": tissue, "left": left, "right": right, **verdict(lv, rv)})
    for filename, data in (("indicators.csv", rows), ("comparisons.csv", pairwise)):
        with (target / filename).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(data[0]))
            writer.writeheader()
            writer.writerows(data)
    manifest = {"software": descriptor["software"], "task": "compare_schedules",
                "request_document": document, "runs": runs, "comparisons": pairwise,
                "criterion": descriptor["comparison_task"]["criterion"],
                "nature": descriptor["nature"], "validity_notes": descriptor["validity_notes"],
                "output_qualification": {"indicators.csv": descriptor["outputs"],
                    "comparisons.csv": {"delta_tcp_percent": "percentage points, left minus right",
                        "delta_ntcp_percent": "percentage points, left minus right",
                        "verdict": "pairwise model comparison; never a clinical recommendation"}}}
    (target / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False,
                                                     indent=2, allow_nan=False), encoding="utf-8")
    return target, {"comparisons": pairwise}
