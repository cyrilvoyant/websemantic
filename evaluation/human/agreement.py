"""Agreement for the blind human evaluation: Cohen's kappa and raw agreement, annotator A vs B and each annotator vs
the automatic scorer on the three items that have an automatic counterpart of the same definition; human-scored
contract effect (F010 vs F000) with Fisher's exact test.
wrong_unit_or_value has no automatic counterpart: the scorer's hallucination flag also counts defaults and conventions
used without acceptance, a different construct, so it is not compared.
Disagreements between A and B are listed in adjudication.xlsx (rows appended, decisions never erased, a decision
reused only while its A and B labels match the current annotations); the effect is reported
on adjudicated labels (agreed + adjudicated) when every disagreement is adjudicated, and separately on agreed labels.
With annotator B empty, results for A alone are provisional (no inter-annotator agreement).
Usage: python agreement.py [--blank-as-no A B] [--single]
  --blank-as-no  annotators who declared that an empty item cell means "no" (their files are not modified)
  --single       annotator A alone, B ignored (provisional)
  --no-adjudication  disagreements kept as legitimate, not adjudicated (amendment of 15 October 2026): effect
                     reported for each annotator and on agreed labels; adjudication.xlsx neither read nor written
Reads benchmark-reserve/human/annotation-A.xlsx, annotation-B.xlsx, key.csv.
"""

import argparse
import csv
from collections import Counter
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font
from scipy.stats import fisher_exact

HUMAN = Path(__file__).resolve().parents[3] / "benchmark-reserve" / "human"
ITEMS = ("decision_correct", "premature_execution", "qualifier_handled", "wrong_unit_or_value", "critical_error")
AUTO = {"decision_correct": "auto_decision_ok", "premature_execution": "auto_premature_execute",
        "qualifier_handled": "auto_qualifier_convention_ok"}
EFFECT = ("premature_execution", "critical_error")


def read(name, blank_as_no=False):
    wb = load_workbook(HUMAN / f"annotation-{name}.xlsx")
    ws = wb["annotation"] if "annotation" in wb.sheetnames else wb.active
    head = [c.value for c in ws[1]]
    rows = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[0] is None:
            continue
        record = dict(zip(head, row))
        for item in ITEMS:
            value = record.get(item)
            value = value.strip() if isinstance(value, str) else value
            record[item] = "no" if blank_as_no and value in (None, "") else (value or None)
        rows[row[0]] = record
    return rows


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


def adjudication(a, b, rows):
    """Final labels for the disagreements, from adjudication.xlsx.
    New disagreements are appended; existing rows and their decisions are never erased. A decision is used only while the
    A and B labels it was taken on still match the current annotations; otherwise its row is marked stale and a new row
    is appended for the current labels."""
    path = HUMAN / "adjudication.xlsx"
    head = ["row", "item", "A", "B", "final", "reason", "status"]
    current = {(r, item): (a[r][item], b[r][item]) for r in rows for item in ITEMS
               if a[r][item] and b[r][item] and a[r][item] != b[r][item]}
    if path.exists():
        wb = load_workbook(path)
        ws = wb["adjudication"]
        if [c.value for c in ws[1]][:len(head)] != head:
            ws.cell(1, 7, "status").font = Font(bold=True)
    else:
        wb = Workbook()
        ws = wb.active
        ws.title = "adjudication"
        ws.append(head)
        for c in ws[1]:
            c.font = Font(bold=True)
    final, valid, changed = {}, set(), 0
    for row in ws.iter_rows(min_row=2):
        r, item, la, lb, decision = (c.value for c in row[:5])
        if r is None:
            continue
        if current.get((r, item)) == (la, lb):
            valid.add((r, item))
            if decision:
                final[(r, item)] = decision
            status = "adjudicated" if decision else "pending"
        else:
            status = "stale: A/B changed since" if (r, item) in current else "no longer a disagreement"
        if row[6].value != status:
            ws.cell(row[0].row, 7, status)
            changed += 1
    added = [(r, item, la, lb) for (r, item), (la, lb) in sorted(current.items()) if (r, item) not in valid]
    for r, item, la, lb in added:
        ws.append([r, item, la, lb, None, None, "pending"])
    if added or changed or not path.exists():
        wb.save(path)
    if added:
        print(f"{len(added)} disagreements added to {path.name}: fill 'final' and 'reason' together; A and B stay unchanged")
    missing = [key for key in current if key not in final]
    return final, missing


def fisher(item, rows, label, key, note):
    table = {c: [0, 0] for c in ("F000", "F010")}
    for r in rows:
        v = label(r)
        if v in ("yes", "no"):
            table[key[r]["condition"]][0 if v == "yes" else 1] += 1
    p = fisher_exact([table["F010"], table["F000"]])[1]
    print(f"{item}: F010 yes/no={table['F010']}  F000 yes/no={table['F000']}  Fisher p={p:.3g} ({note})")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--blank-as-no", nargs="*", default=[], choices=("A", "B"))
    parser.add_argument("--single", action="store_true")
    parser.add_argument("--no-adjudication", action="store_true")
    args = parser.parse_args(argv)
    a, b = read("A", "A" in args.blank_as_no), read("B", "B" in args.blank_as_no)
    key = {int(r["row"]): r for r in csv.DictReader((HUMAN / "key.csv").open(encoding="utf-8"))}
    rows = sorted(set(a) & set(b))
    single = args.single or not any(b[r][item] for r in rows for item in ITEMS)  # A alone
    if args.blank_as_no:
        print("empty cells read as 'no' for annotator(s) " + ", ".join(args.blank_as_no) + " (declared by the annotator)")
    print(f"{len(rows)} rows" + (" | PROVISIONAL: A alone, no inter-annotator agreement" if single else ""))
    for item in ITEMS:
        line = f"{item:20}"
        if not single:
            k, n, po = kappa([a[r][item] for r in rows], [b[r][item] for r in rows])
            line += f" A vs B: kappa={k if k is None else round(k, 3)} agreement={po if po is None else round(po, 3)} n={n}"
        if item in AUTO:
            auto = [as_yesno(key[r][AUTO[item]]) for r in rows]
            for name, ann in (("A", a),) if single else (("A", a), ("B", b)):
                vals = [None if ann[r][item] in ("unsure", "n/a") else ann[r][item] for r in rows]
                k2, n2, po2 = kappa(vals, auto)
                line += f" | {name} vs scorer kappa={k2 if k2 is None else round(k2, 3)} agreement={po2 if po2 is None else round(po2, 3)} (n={n2})"
        else:
            line += " | no automatic counterpart"
        print(line)
    if single:
        for item in EFFECT:
            fisher(item, rows, lambda r: a[r][item], key, "annotator A alone, provisional")
        return
    if args.no_adjudication:
        for item in EFFECT:
            fisher(item, rows, lambda r: a[r][item], key, "annotator A")
            fisher(item, rows, lambda r: b[r][item], key, "annotator B")
            fisher(item, rows, lambda r: a[r][item] if a[r][item] == b[r][item] else None, key,
                   "agreed labels only; disagreements kept, not adjudicated")
        return
    final, missing = adjudication(a, b, rows)
    for item in EFFECT:
        fisher(item, rows, lambda r: a[r][item] if a[r][item] == b[r][item] else None, key, "agreed labels only")
        if any(i == item for _, i in missing):
            print(f"  adjudicated analysis pending: {sum(i == item for _, i in missing)} disagreements on {item} not adjudicated")
        else:
            fisher(item, rows, lambda r: a[r][item] if a[r][item] == b[r][item] else final.get((r, item)), key,
                   "adjudicated labels: agreed + adjudicated")


if __name__ == "__main__":
    main()
