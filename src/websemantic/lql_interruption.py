"""Biologically equivalent resumption of an interrupted fictitious schedule, with the unchanged LQL-Equiv library.

Given the planned schedule, the sessions already given, the interruption and the number of sessions still possible,
the module finds, for the tumour and for each organ at risk, the dose per session that gives back the planned EQD2 of
that tissue, for every possible number of remaining sessions (the library's time factor and its 2014 options
included, as in the reviewed adapter). It also reports what the tumour-equivalent schedule does to each organ, as a
difference from its planned EQD2. This is the ideal schedule from a simulation point of view, tissue by tissue; the
practitioner decides in the clinical context. Fictitious scenarios only, research and education.
"""

import math
from dataclasses import asdict, dataclass

from websemantic.adapters.lql import _backend

RESOLUTION_GY = 0.01
SCOPE = ("Simulation of a fictitious scenario (research and education): the biologically equivalent schedule of each "
         "tissue according to the model; the practitioner decides in the clinical context.")


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


def check(s):
    if not s.organs:
        raise ValueError("At least one organ at risk is required.")
    if not (s.planned_dose > 0 and s.reference_dose > 0 and s.max_dose_per_session > 0):
        raise ValueError("Doses must be positive.")
    if not all(isinstance(v, int) and not isinstance(v, bool)
               for v in (s.planned_sessions, s.done_sessions, s.max_remaining)):
        raise ValueError("Session counts must be integers.")
    if not 0 <= s.done_sessions < s.planned_sessions:
        raise ValueError("Sessions already given must be fewer than the planned sessions.")
    if s.max_remaining < 1 or s.gap_days < 0:
        raise ValueError("At least one remaining session and a non-negative interruption are required.")


class _Model:
    """The sha256-verified library (same loader and options as the reviewed adapter)."""

    def __init__(self, workspace, descriptor, situation):
        self.m = _backend(workspace, descriptor)
        library = self.m.load_library()
        self.tumour = library.tumour_site(situation.tumour)
        self.organs = {name: library.organ(name) for name in situation.organs}
        self.reference = situation.reference_dose

    def eqd2(self, organ, courses):
        """(tumour EQD2, organ EQD2), None outside the library's validity domain."""
        prescription = self.m.Prescription(courses=tuple(self.m.Course(d, n, g) for d, n, g in courses if n > 0),
                                           reference_dose=self.reference)
        r = self.m.compute(self.organs[organ], self.tumour, prescription, options=self.m.Options())
        tumour_ok = r.tumour_total_valid and not any(c.tumour_saturated for c in r.courses)
        oar_ok = r.oar_total_valid and not any(c.oar_saturated for c in r.courses)
        return (r.eqd_tumour_total if tumour_ok else None), (r.eqd_oar_total if oar_ok else None)


def _iso_dose(effect, target, top):
    """Smallest dose per session (0.01 Gy grid) whose effect reaches the target; None if out of reach."""
    reached = effect(top)
    if reached is None or reached < target:
        return None
    lo, hi = RESOLUTION_GY, top
    while hi - lo > RESOLUTION_GY / 4:
        mid = (lo + hi) / 2
        value = effect(mid)
        if value is not None and value >= target:
            hi = mid
        else:
            lo = mid
    dose = round(math.ceil(hi / RESOLUTION_GY - 1e-9) * RESOLUTION_GY, 2)
    # The 2014 model quantises equivalent fractions: the effect is a staircase, so settle on the grid point where
    # the target is reached and the next lower point is not.
    while (effect(dose) or 0) < target and dose < top:
        dose = round(dose + RESOLUTION_GY, 2)
    while dose - RESOLUTION_GY > 0 and (effect(round(dose - RESOLUTION_GY, 2)) or 0) >= target:
        dose = round(dose - RESOLUTION_GY, 2)
    return dose


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

    rows = []
    for n in range(1, s.max_remaining + 1):
        tumour_dose = _iso_dose(lambda d: model.eqd2(first, schedule(d, n))[0], plan_tumour, s.max_dose_per_session)
        row = {"sessions": n, "tumour": tumour_dose, "organs": {}}
        for o in s.organs:
            organ_dose = (None if plan_organs[o] is None else
                          _iso_dose(lambda d: model.eqd2(o, schedule(d, n))[1], plan_organs[o], s.max_dose_per_session))
            excess = None
            if tumour_dose is not None and plan_organs[o]:
                under_tumour_plan = model.eqd2(o, schedule(tumour_dose, n))[1]
                if under_tumour_plan is not None:
                    excess = round(100 * (under_tumour_plan / plan_organs[o] - 1), 1)
            row["organs"][o] = {"equivalent_dose": organ_dose, "excess_with_tumour_schedule_percent": excess}
        rows.append(row)

    reference = rows[-1]  # all the sessions still possible: the closest to the planned fractionation
    left = min(s.max_remaining, s.planned_sessions - s.done_sessions)
    uncompensated = model.eqd2(first, schedule(s.planned_dose, left))[0]
    return {
        "situation": asdict(s),
        "planned": {"tumour_eqd2": plan_tumour, "organs_eqd2": plan_organs},
        "uncompensated": {"sessions": left, "dose_per_session": s.planned_dose, "tumour_eqd2": uncompensated,
                          "tumour_deficit_percent": round(100 * (uncompensated / plan_tumour - 1), 1)
                          if uncompensated is not None else None},
        "equivalent": rows,
        "ideal": {"sessions": reference["sessions"], "tumour": reference["tumour"],
                  "organs": {o: v["equivalent_dose"] for o, v in reference["organs"].items()},
                  "organ_excess_with_tumour_schedule_percent":
                      {o: v["excess_with_tumour_schedule_percent"] for o, v in reference["organs"].items()}},
        "scope": SCOPE,
    }
