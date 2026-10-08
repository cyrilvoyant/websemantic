"""Agreement for the blind human evaluation: Cohen's kappa and raw agreement, annotator A vs B and each annotator vs
the automatic scorer; human-scored contract effect (F010 vs F000) with Fisher's exact test.
Usage: python agreement.py   (reads benchmark-reserve/human/annotation-A.xlsx, annotation-B.xlsx, key.csv)
"""

import csv
from collections import Counter
from pathlib import Path

from openpyxl import load_workbook
from scipy.stats import fisher_exact

HUMAN = Path(__file__).resolve().parents[3] / "benchmark-reserve" / "human"
ITEMS = ("decision_correct", "premature_execution", "qualifier_handled", "wrong_unit_or_value", "critical_error")
AUTO = {"decision_correct": "auto_decision_ok", "premature_execution": "auto_premature_execute",
        "qualifier_handled": "auto_qualifier_convention_ok"}


def read(name):
    ws = load_workbook(HUMAN / f"annotation-{name}.xlsx").active
    head = [c.value for c in ws[1]]
    return {row[0]: dict(zip(head, row)) for row in ws.iter_rows(min_row=2, values_only=True) if row[0] is not None}


def kappa(a, b):
    pairs = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
    if not pairs:
        return None, 0, None
    n = len(pairs)
    po = sum(x == y for x, y in pairs) / n
    ca, cb = Counter(x for x, _ in pairs), Counter(y for _, y in pairs)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / n ** 2
    return (None if pe == 1 else (po - pe) / (1 - pe)), n, po


def as_yesno(v):
    return None if v in ("", None) else ("yes" if float(v) > 0 else "no")


def main():
    a, b = read("A"), read("B")
    key = {int(r["row"]): r for r in csv.DictReader((HUMAN / "key.csv").open(encoding="utf-8"))}
    rows = sorted(set(a) & set(b))
    print(f"{len(rows)} rows annotated by both")
    for item in ITEMS:
        k, n, po = kappa([a[r][item] for r in rows], [b[r][item] for r in rows])
        line = f"{item:20} A vs B: kappa={k if k is None else round(k, 3)} agreement={po if po is None else round(po, 3)} n={n}"
        if item in AUTO:
            auto = [as_yesno(key[r][AUTO[item]]) for r in rows]
            for name, ann in (("A", a), ("B", b)):
                vals = [None if ann[r][item] in ("unsure", "n/a") else ann[r][item] for r in rows]
                k2, n2, _ = kappa(vals, auto)
                line += f" | {name} vs scorer kappa={k2 if k2 is None else round(k2, 3)} (n={n2})"
        print(line)
    for item in ("premature_execution", "critical_error"):
        table = {c: [0, 0] for c in ("F000", "F010")}
        for r in rows:
            v = a[r][item] if a[r][item] == b[r][item] else None  # agreed labels only
            if v in ("yes", "no"):
                table[key[r]["condition"]][0 if v == "yes" else 1] += 1
        p = fisher_exact([table["F010"], table["F000"]])[1]
        print(f"{item}: F010 yes/no={table['F010']}  F000 yes/no={table['F000']}  Fisher p={p:.3g} (agreed labels)")


if __name__ == "__main__":
    main()
