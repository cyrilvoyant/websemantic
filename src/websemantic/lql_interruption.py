"""Biologically equivalent resumption of an interrupted fictitious schedule, with the unchanged LQL-Equiv library.

Only LQL-Equiv computes. Given the planned schedule, the sessions already given, the interruption and the number of
sessions still possible, the module runs the library on candidate remaining schedules and keeps, for the tumour and
for each organ at risk separately, the first dose per session (0.01 Gy grid, within the search bound) whose EQD2
reaches the planned EQD2 of that tissue. The library is loaded by the reviewed adapter's sha256-checked loader and
called with the same options as that adapter: the library's current defaults (legacy_quantisation=False,
reproduce_2014=False, staircase time model, logistic TCP). The search only chooses the doses to try.

Criterion: biological equivalence (equal EQD2), not complication minimisation. The equivalent schedules of the
different tissues are separate results; they do not form one schedule equivalent for all tissues. Simulation of a
fictitious scenario for research and education; the practitioner decides in the clinical context.
"""

import math
from dataclasses import asdict, dataclass

from websemantic.adapters.lql import _backend

RESOLUTION_GY = 0.01
SCOPE = ("Simulation of a fictitious scenario (research and education): for each tissue separately, the first dose "
         "per session on a 0.01 Gy grid whose LQL-Equiv EQD2 reaches the planned EQD2; the practitioner decides in "
         "the clinical context.")
LIMITS = {"planned_dose": 30.0, "reference_dose": 10.0, "max_dose_per_session": 30.0, "gap_days": 365.0,
          "planned_sessions": 100, "max_remaining": 60}  # input sanity limits, not clinical limits


@dataclass(frozen=True)
class Situation:
    tumour: str
    organs: tuple
    planned_dose: float  # Gy per session
    planned_sessions: int
    done_sessions: int
    gap_days: float  # interruption before the remaining sessions
    max_remaining: int  # sessions still possible
    reference_dose: float = 2.0
    max_dose_per_session: float = 10.0  # search bound only


def _real(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def check(s):
    if not s.organs or not all(isinstance(o, str) and o for o in s.organs):
        raise ValueError("At least one organ at risk is required.")
    for name in ("planned_dose", "reference_dose", "max_dose_per_session", "gap_days"):
        value = getattr(s, name)
        if not _real(value):
            raise ValueError(f"{name} must be a finite number.")
        if value > LIMITS[name]:
            raise ValueError(f"{name} exceeds the input limit {LIMITS[name]}.")
    if not (s.planned_dose > 0 and s.reference_dose > 0 and s.max_dose_per_session > 0):
        raise ValueError("Doses must be positive.")
    if not all(isinstance(v, int) and not isinstance(v, bool)
               for v in (s.planned_sessions, s.done_sessions, s.max_remaining)):
        raise ValueError("Session counts must be integers.")
    if s.planned_sessions > LIMITS["planned_sessions"] or s.max_remaining > LIMITS["max_remaining"]:
        raise ValueError("Session counts exceed the input limits.")
    if not 0 <= s.done_sessions < s.planned_sessions:
        raise ValueError("Sessions already given must be fewer than the planned sessions.")
    if s.max_remaining < 1 or s.gap_days < 0:
        raise ValueError("At least one remaining session and a non-negative interruption are required.")


class _Model:
    """The sha256-verified library, loaded and called exactly as in the reviewed adapter."""

    def __init__(self, workspace, descriptor, situation):
        self.m = _backend(workspace, descriptor)
        library = self.m.load_library()
        self.tumour = library.tumour_site(situation.tumour)
        self.organs = {name: library.organ(name) for name in situation.organs}
        self.reference = situation.reference_dose

    def eqd2(self, organ, courses):
        """(tumour EQD2, organ EQD2) from LQL-Equiv; None outside the library's validity domain."""
        prescription = self.m.Prescription(courses=tuple(self.m.Course(d, n, g) for d, n, g in courses if n > 0),
                                           reference_dose=self.reference)
        r = self.m.compute(self.organs[organ], self.tumour, prescription, options=self.m.Options())
        tumour_ok = r.tumour_total_valid and not any(c.tumour_saturated for c in r.courses)
        oar_ok = r.oar_total_valid and not any(c.oar_saturated for c in r.courses)
        return (r.eqd_tumour_total if tumour_ok else None), (r.eqd_oar_total if oar_ok else None)


def _grid(dose):
    return round(round(dose / RESOLUTION_GY) * RESOLUTION_GY, 2)


def _iso_dose(effect, target, top):
    """First grid dose <= top whose effect reaches the target, with the effect obtained; (None, None) if none.

    The search only chooses which doses to try; every effect value comes from the library. A top bound outside the
    validity domain is not read as 'out of reach': the largest valid grid point below it is used instead.
    """
    top = math.floor(top / RESOLUTION_GY + 1e-9) * RESOLUTION_GY
    hi, value = _grid(top), effect(_grid(top))
    while value is None and hi > RESOLUTION_GY:  # walk down to the validity domain (0.25 Gy steps, then refine)
        hi = _grid(max(RESOLUTION_GY, hi - 0.25))
        value = effect(hi)
    if value is None or value < target:
        return None, None
    lo = RESOLUTION_GY
    while hi - lo > RESOLUTION_GY / 2:
        mid = _grid((lo + hi) / 2)
        if mid in (lo, hi):
            break
        v = effect(mid)
        if v is not None and v >= target:
            hi = mid
        else:
            lo = mid
    # settle on the grid point where the target is reached and the next lower point is not (staircase time model)
    while hi - RESOLUTION_GY > 0:
        lower = effect(_grid(hi - RESOLUTION_GY))
        if lower is None or lower < target:
            break
        hi = _grid(hi - RESOLUTION_GY)
    final = effect(hi)
    if final is None or final < target or hi > top + 1e-9:
        return None, None
    return hi, final


def resume(situation, workspace, descriptor):
    """Biologically equivalent resumption, tissue by tissue. Returns plain data (JSON-ready)."""
    s = situation
    check(s)
    model = _Model(workspace, descriptor, s)
    first = s.organs[0]
    planned = [(s.planned_dose, s.planned_sessions, 0.0)]
    done = (s.planned_dose, s.done_sessions, 0.0)
    plan_tumour = model.eqd2(first, planned)[0]
    if plan_tumour is None:
        raise ValueError("The planned schedule is outside the library's validity domain.")
    plan_organs = {o: model.eqd2(o, planned)[1] for o in s.organs}

    def schedule(d, n):
        return [done, (d, n, s.gap_days)]

    def entry(dose, obtained, target):
        if dose is None:
            return {"dose_per_session": None}
        return {"dose_per_session": dose, "target_eqd2": target, "obtained_eqd2": obtained,
                "difference_gy": obtained - target}

    rows = []
    for n in range(1, s.max_remaining + 1):
        dose, obtained = _iso_dose(lambda d, n=n: model.eqd2(first, schedule(d, n))[0], plan_tumour, s.max_dose_per_session)
        row = {"sessions": n, "tumour": entry(dose, obtained, plan_tumour), "organs": {}}
        for o in s.organs:
            if plan_organs[o] is None:
                row["organs"][o] = {"equivalent": {"dose_per_session": None}, "eqd2_with_tumour_schedule": None,
                                    "difference_with_tumour_schedule_percent": None}
                continue
            odose, oobt = _iso_dose(lambda d, o=o, n=n: model.eqd2(o, schedule(d, n))[1], plan_organs[o],
                                    s.max_dose_per_session)
            under = model.eqd2(o, schedule(dose, n))[1] if dose is not None else None
            row["organs"][o] = {"equivalent": entry(odose, oobt, plan_organs[o]), "eqd2_with_tumour_schedule": under,
                                "difference_with_tumour_schedule_percent":
                                    None if under is None else round(100 * (under / plan_organs[o] - 1), 1)}
        rows.append(row)

    last = rows[-1]  # all the sessions still possible: the closest to the planned fractionation
    left = min(s.max_remaining, s.planned_sessions - s.done_sessions)
    uncompensated = model.eqd2(first, schedule(s.planned_dose, left))[0]
    return {
        "situation": asdict(s),
        "options": "library defaults, as in the reviewed adapter (legacy_quantisation=False, reproduce_2014=False, "
                   "staircase time model, logistic TCP)",
        "resolution_gy": RESOLUTION_GY,
        "planned": {"tumour_eqd2": plan_tumour, "organs_eqd2": plan_organs},
        "uncompensated": {"sessions": left, "dose_per_session": s.planned_dose, "tumour_eqd2": uncompensated,
                          "tumour_difference_percent": round(100 * (uncompensated / plan_tumour - 1), 1)
                          if uncompensated is not None else None},
        "equivalent": rows,
        "with_all_remaining_sessions": {
            "sessions": last["sessions"], "tumour": last["tumour"]["dose_per_session"],
            "organs": {o: v["equivalent"]["dose_per_session"] for o, v in last["organs"].items()},
            "organ_difference_with_tumour_schedule_percent":
                {o: v["difference_with_tumour_schedule_percent"] for o, v in last["organs"].items()}},
        "scope": SCOPE,
    }
