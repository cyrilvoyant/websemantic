"""Worked end-to-end case requested by Cyril (9 October 2026): a spoken request to a phone agent.

"Je voudrais connaître la dose équivalente d'un patient traité pour un cancer de la prostate avec un schéma classique
de radiothérapie externe ; il a eu deux semaines d'arrêt dès la deuxième semaine et il doit finir dans quatre semaines
au maximum. Pour le volume cible et tous les organes à risque."

1. First turn: the model (Codestral, temperature 0) receives the request with the documentation alone (F000) and with
   the current contract (F010, which includes the anatomical groups); both answers are stored.
2. Checks of the stored first answers, without any new model call: the Python gate of the application
   (src/websemantic/core/validation.py; E1 values mapped literally to the descriptor fields; a default or assumption
   is not accepted in a first turn, since only the user can accept it) and the SHACL range and relational rules
   (validate_answers.classify).
3. Following turn, specified by the authors (fictitious, not generated): the user accepts the conventional 2 Gy per
   fraction, gives the planned total (78 Gy in 39 fractions) and the 10 sessions given before the 14-day gap, and
   accepts 20 remaining sessions at 2.9 Gy (the 58 Gy left) within four weeks after resumption (5 sessions a week).
   The resulting two-course scenario is checked with the SHACL rules (one group instance per course).
4. The pinned LQL-Equiv code computes the planned schedule (39 x 2 Gy) and the delivered one (10 x 2 Gy, 14-day gap,
   20 x 2.9 Gy) for the prostate target and every organ of the pelvic group of the descriptor. The library is called
   directly: a two-course schedule is outside the tasks the descriptor currently declares, so the application gate
   would not run it.
Output (private): voice-case.json. Usage: python voice_case.py [--refresh] (--refresh calls the model again)
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "external" / "LQL-Equiv-web" / "src"))
import yaml  # noqa: E402

import run_e1  # noqa: E402
import validate_answers  # noqa: E402
from lqlequiv.model import Course, Prescription, compute  # noqa: E402

sys.path.insert(0, str(ROOT / "src"))
from websemantic.core.validation import Parameter, Scenario, validate  # noqa: E402

REQUEST = ("Je voudrais connaître la dose équivalente d'un patient traité pour un cancer de la prostate avec un schéma "
           "classique de radiothérapie externe ; il a eu deux semaines d'arrêt dès la deuxième semaine et il doit finir "
           "dans quatre semaines au maximum. Pour le volume cible et tous les organes à risque.")


def first_turn():
    run_e1.load_key()
    out = {}
    for cond in ("F000", "F010"):
        prompt = run_e1.INSTRUCTIONS + "\n\n" + run_e1.context("lqlequiv", cond) + "\n\n## User request\n" + REQUEST
        text, usage = run_e1.mistral(prompt, "codestral-latest")
        parsed, how = run_e1.extract_json(text)
        out[cond] = {"parsed": parsed, "extraction": how, "usage": usage}
    return out


def descriptor():
    return yaml.safe_load((ROOT / "descriptors" / "lqlequiv" / "descriptor.yaml").read_text(encoding="utf-8"))


def gate(parsed):
    """Python gate on a stored answer: fields and units taken literally, nothing accepted on the user's behalf."""
    d = descriptor()
    groups = {"inputs": {}, "experiment": {}}
    for v in parsed.get("values") or []:
        name = str(v.get("field"))
        group = "experiment" if name in (d.get("experiment") or {}) else "inputs"
        origin = {"default_accepted": "default"}.get(v.get("origin"), v.get("origin") or "missing")
        groups[group][name] = Parameter(value=v.get("value"), unit=v.get("unit"), origin=origin,
                                        evidence=v.get("evidence") or None, accepted=False)
    result = validate(Scenario(REQUEST, d["tasks"]["supported"][0], groups["inputs"], groups["experiment"]), d)
    return {"decision": result.decision, "issues": [vars(i) for i in result.issues]}


def shacl(values):
    rules = validate_answers.shapes()
    status, messages, mapped, unmapped = validate_answers.classify(
        {"parsed": {"values": values}}, validate_answers.concepts("lqlequiv"), *rules)
    return {"status": status, "messages": messages, "mapped": len(mapped), "unmapped": unmapped}


FOLLOW_UP = [{"field": "organ", "value": "Rectum"}, {"field": "tumour_site", "value": "Prostate"},
             {"field": "courses", "value": [{"dose_per_fraction": 2.0, "n_fractions": 10, "gap_days": 0.0,
                                             "total_dose": 20.0},
                                            {"dose_per_fraction": 2.9, "n_fractions": 20, "gap_days": 14.0,
                                             "total_dose": 58.0}]},
             {"field": "reference_dose", "value": 2.0}]


def calculation():
    d = yaml.safe_load((ROOT / "descriptors" / "lqlequiv" / "descriptor.yaml").read_text(encoding="utf-8"))
    organs = d["anatomical_groups"]["pelvis"]["organs"]
    planned = Prescription(courses=(Course(2.0, 39, 0.0),), reference_dose=2.0)
    delivered = Prescription(courses=(Course(2.0, 10, 0.0), Course(2.9, 20, 14.0)), reference_dose=2.0)
    rows = []
    for organ in organs:
        r = {"organ": organ}
        for name, presc in (("planned", planned), ("delivered", delivered)):
            res = compute(organ, "Prostate", presc)
            r[name] = {"eqd_oar": res.eqd_oar_total, "eqd_tumour": res.eqd_tumour_total, "ntcp_percent": res.ntcp_percent,
                       "tcp_percent": res.tcp_percent, "saturated": res.saturated}
        rows.append(r)
    return rows


if __name__ == "__main__":
    stored = HERE / "voice-case.json"
    turn = first_turn() if "--refresh" in sys.argv or not stored.exists() else \
        json.loads(stored.read_text(encoding="utf-8"))["first_turn"]
    case = {"request": REQUEST, "first_turn": turn,
            "checks_first_turn": {c: {"python_gate": gate(a["parsed"] or {}),
                                      "shacl": shacl((a["parsed"] or {}).get("values") or [])} for c, a in turn.items()},
            "follow_up_specified": {"values": FOLLOW_UP, "shacl": shacl(FOLLOW_UP),
                                    "note": "Specified by the authors (fictitious); four weeks after resumption."},
            "calculation": calculation()}
    (HERE / "voice-case.json").write_text(json.dumps(case, indent=1, ensure_ascii=False), encoding="utf-8")
    for cond, a in case["first_turn"].items():
        p = a["parsed"] or {}
        print(cond, p.get("decision"), "|", [q for q in p.get("questions") or []])
        chk = case["checks_first_turn"][cond]
        print("   gate:", chk["python_gate"]["decision"], sorted({i["code"] for i in chk["python_gate"]["issues"]}),
              "| shacl:", chk["shacl"]["status"], chk["shacl"]["unmapped"])
        print("   values:", [(v.get("field"), v.get("value"), v.get("origin")) for v in p.get("values") or []])
    print("follow-up shacl:", case["follow_up_specified"]["shacl"]["status"])
    for r in case["calculation"]:
        print(r["organ"], {k: {kk: (round(vv, 1) if isinstance(vv, float) else vv) for kk, vv in v.items()}
                           for k, v in r.items() if k != "organ"})
