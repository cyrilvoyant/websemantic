"""Worked end-to-end case requested by Cyril (9 October 2026): a spoken request to a phone agent.

"Je voudrais connaître la dose équivalente d'un patient traité pour un cancer de la prostate avec un schéma classique
de radiothérapie externe ; il a eu deux semaines d'arrêt dès la deuxième semaine et il doit finir dans quatre semaines
au maximum. Pour le volume cible et tous les organes à risque."

1. First turn: the model (Codestral, temperature 0) receives the request with the documentation alone (F000) and with
   the current contract (F010, which includes the anatomical groups); both answers are stored.
2. Following turn (stated, not generated): the user accepts the conventional 2 Gy per fraction, gives the planned
   total (78 Gy in 39 fractions), and accepts 20 remaining sessions at 2.9 Gy (the 58 Gy left, within four weeks).
3. The pinned LQL-Equiv code computes the planned schedule (39 x 2 Gy) and the delivered one (10 x 2 Gy, 14-day gap,
   20 x 2.9 Gy) for the prostate target and every organ of the pelvic group of the descriptor.
Output (private): voice-case.json. Usage: python voice_case.py
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
from lqlequiv.model import Course, Prescription, compute  # noqa: E402

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
    case = {"request": REQUEST, "first_turn": first_turn(), "calculation": calculation()}
    (HERE / "voice-case.json").write_text(json.dumps(case, indent=1, ensure_ascii=False), encoding="utf-8")
    for cond, a in case["first_turn"].items():
        p = a["parsed"] or {}
        print(cond, p.get("decision"), "|", [q for q in p.get("questions") or []])
        print("   values:", [(v.get("field"), v.get("value"), v.get("origin")) for v in p.get("values") or []])
    for r in case["calculation"]:
        print(r["organ"], {k: {kk: (round(vv, 1) if isinstance(vv, float) else vv) for kk, vv in v.items()}
                           for k, v in r.items() if k != "organ"})
