"""Preregistered ToolRosella baseline (evaluation/PREREG-toolrosella-and-human.md): T/TC against F000/F010.

Unit: unique first-turn request, repetitions averaged, same definition as request_level.py. Contrasts per model, three
codes pooled: T vs F000, TC vs T, TC vs F010 (paired Wilcoxon signed-rank, zero differences discarded); Holm correction
over the six primary tests on premature execution (three contrasts x two open models). Per-code values and the other
metrics are descriptive. A code whose ToolRosella conversion failed has no tool block, so its T and TC contexts equal the
campaign F000 and F010 (checked by context hash) and those answers are used. The exploratory TX/TCX conditions give
the tools generated for failed conversions too; for a successful conversion TX/TCX equal T/TC.
Usage: python toolrosella_effect.py <campaign_folder>:<toolrosella_folder> [...]   (one pair per model)
"""

import csv
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

from scipy.stats import wilcoxon

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from length_control import holm  # noqa: E402
from request_level import RESERVE, first_turns  # noqa: E402

METRICS = ("premature_execute", "decision_ok", "qualifier_convention_ok")
RUN = os.environ.get("WS_TOOLROSELLA_RUN", "toolrosella-20261008T173041Z")  # same selector as run_e1.py
STATUS = json.loads((RESERVE / "toolrosella" / RUN / "status.json").read_text(encoding="utf-8"))
FAILED = {d for d, s in STATUS["codes"].items() if s["conversion"] != "success"}
PRIMARY = (("T", "F000"), ("TC", "T"), ("TC", "F010"))
EXPLORATORY = (("TX", "F000"), ("TCX", "TX"), ("TCX", "F010"))


def alias(domain, condition):
    """Condition actually answered for (domain, condition): failed conversions reuse the campaign F000/F010."""
    if domain in FAILED and condition in ("T", "TC"):
        return {"T": "F000", "TC": "F010"}[condition]
    if domain not in FAILED and condition in ("TX", "TCX"):
        return {"TX": "T", "TCX": "TC"}[condition]
    return condition


def means(folders, turns):
    acc = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    hashes = defaultdict(set)
    for folder in folders:
        for r in csv.DictReader((HERE / f"e1-scores-{folder}.csv").open(encoding="utf-8")):
            unit = (r["domain"], turns[r["case_id"]])
            hashes[(r["domain"], r["condition"])].add(r["context"])
            for m in METRICS:
                if r.get(m) not in ("", None):
                    acc[unit][r["condition"]][m].append(float(r[m]))
    return {u: {c: {m: sum(v) / len(v) for m, v in ms.items()} for c, ms in cs.items()} for u, cs in acc.items()}, hashes


def main(pairs):
    turns = first_turns()
    rows = []
    for pair in pairs:
        campaign, baseline = pair.split(":")
        data, _ = means([campaign, baseline], turns)
        model = baseline.split("__")[0].replace("local_", "")
        for family, contrasts in (("primary", PRIMARY), ("exploratory", EXPLORATORY)):
            for a, b in contrasts:
                for m in METRICS:
                    for dom in ("all", "tls", "lqlequiv", "pyrcel"):
                        d = []
                        for (u_dom, _), cs in data.items():
                            if dom != "all" and u_dom != dom:
                                continue
                            ca, cb = alias(u_dom, a), alias(u_dom, b)
                            if m in cs.get(ca, {}) and m in cs.get(cb, {}):
                                d.append(cs[ca][m] - cs[cb][m])
                        if not d:
                            continue
                        nz = [x for x in d if abs(x) > 1e-12]
                        rows.append({"model": model, "family": family, "contrast": f"{a} vs {b}", "metric": m,
                                     "domain": dom, "requests": len(d), "mean_difference": round(sum(d) / len(d), 4),
                                     "higher": sum(x > 1e-12 for x in d), "lower": sum(x < -1e-12 for x in d),
                                     "wilcoxon_p": round(float(wilcoxon(nz).pvalue), 6) if nz else 1.0})
    primary = [r for r in rows if r["family"] == "primary" and r["metric"] == "premature_execute" and r["domain"] == "all"
               and r["model"] in ("mistral-small-3.2-24b", "qwen2.5-72b")]
    for r, p in zip(primary, holm([r["wilcoxon_p"] for r in primary])):
        r["holm_p"] = round(p, 6)
    out = HERE / "e1-toolrosella.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["model", "family", "contrast", "metric", "domain", "requests",
                                           "mean_difference", "higher", "lower", "wilcoxon_p", "holm_p"])
        w.writeheader()
        w.writerows(rows)
    print("failed conversions (T/TC = campaign F000/F010):", sorted(FAILED))
    for r in rows:
        if r["domain"] == "all":
            print(f"{r['model'][:14]:14} {r['family'][:5]} {r['contrast']:11} {r['metric'][:12]:12} n={r['requests']:2} "
                  f"diff={r['mean_difference']:+.3f} +{r['higher']}/-{r['lower']} p={r['wilcoxon_p']:.3g}"
                  + (f" holm={r['holm_p']:.3g}" if "holm_p" in r else ""))


if __name__ == "__main__":
    main(sys.argv[1:])
