"""LQL-Equiv workbench: several schedules for several organs at risk, maximum dose and resumption, with the
unchanged pinned library.

Only LQL-Equiv computes: the library is loaded by the reviewed adapter's sha256-checked loader and called with the
adapter's options and validity rules (an EQD2 or probability is withheld when invalid or saturated). Groups of organs
come from the ontology (ontology/lqlequiv.ttl, SKOS collections), never from a language model. The maximum dose and
the resumption use lql_interruption (first 0.01 Gy grid dose whose EQD2 reaches the target, per tissue).
Fictitious scenarios for research and education; the practitioner decides in the clinical context.
"""

import math
from dataclasses import asdict, dataclass
from pathlib import Path

from websemantic.adapters.lql import EXPECTED_COMMIT, EXPECTED_FILES, _backend
from websemantic.lql_interruption import Situation, resume

LIMITS = {"dose": 30.0, "sessions": 100, "gap_days": 365.0}  # input sanity limits, not clinical limits


@dataclass(frozen=True)
class Schedule:
    dose: float  # Gy per session
    sessions: int
    gap_days: float = 0.0  # interruption, as in the library's course definition

    def check(self):
        if not (isinstance(self.dose, (int, float)) and math.isfinite(self.dose) and 0 < self.dose <= LIMITS["dose"]):
            raise ValueError("Dose per session must be a finite number between 0 and 30 Gy.")
        if not (isinstance(self.sessions, int) and not isinstance(self.sessions, bool)
                and 1 <= self.sessions <= LIMITS["sessions"]):
            raise ValueError("The number of sessions must be an integer between 1 and 100.")
        if not (isinstance(self.gap_days, (int, float)) and math.isfinite(self.gap_days)
                and 0 <= self.gap_days <= LIMITS["gap_days"]):
            raise ValueError("The interruption must be between 0 and 365 days.")


def anatomy(workspace):
    """Anatomical groups read from the ontology: {key: {label, iri, sites, organs}}."""
    from rdflib import RDF, Graph
    from rdflib.namespace import SKOS
    graph = Graph().parse(Path(workspace) / "ontology" / "lqlequiv.ttl")
    groups = {}
    for group in graph.subjects(RDF.type, SKOS.Collection):
        members = list(graph.objects(group, SKOS.member))
        name = lambda m: str(graph.value(m, SKOS.prefLabel))  # noqa: E731
        groups[str(group).rsplit("_group_", 1)[-1]] = {
            "label": str(graph.value(group, SKOS.prefLabel)), "iri": str(group),
            "sites": sorted(name(m) for m in members if "_site_" in str(m)),
            "organs": sorted(name(m) for m in members if "_organ_" in str(m))}
    return dict(sorted(groups.items()))


def group_of_site(groups, site):
    """The first anatomical group (in key order) that contains this tumour site, or None."""
    return next((key for key, g in groups.items() if site in g["sites"]), None)


def _provenance(module, descriptor):
    return {"software": descriptor["software"], "options": {k: str(v) for k, v in asdict(module.Options()).items()},
            "source_verification": {"method": "sha256_lf", "commit": EXPECTED_COMMIT, "files": EXPECTED_FILES}}


def table(workspace, descriptor, tumour, organs, schedules, reference_dose=2.0):
    """One LQL-Equiv computation per schedule and organ at risk; the adapter's validity rules."""
    if not organs or not schedules:
        raise ValueError("At least one organ at risk and one schedule are required.")
    for schedule in schedules:
        schedule.check()
    module = _backend(workspace, descriptor)
    library = module.load_library()
    target, tissues = library.tumour_site(tumour), {name: library.organ(name) for name in organs}
    rows = []
    for schedule in schedules:
        prescription = module.Prescription(courses=(module.Course(schedule.dose, schedule.sessions, schedule.gap_days),),
                                           reference_dose=reference_dose)
        for name in organs:
            r = module.compute(tissues[name], target, prescription, options=module.Options())
            course = r.courses[0]
            oar_ok = r.oar_total_valid and not course.oar_saturated
            tumour_ok = r.tumour_total_valid and not course.tumour_saturated
            row = {"schedule": asdict(schedule), "organ": name, "physical_dose_gy": schedule.dose * schedule.sessions,
                   "bed_tumour": course.bed_tumour if r.tumour_total_valid else None,
                   "eqd_tumour_total": r.eqd_tumour_total if tumour_ok else None,
                   "tcp_percent": r.tcp_percent if tumour_ok else None,
                   "bed_oar": course.bed_oar if r.oar_total_valid else None,
                   "eqd_oar_total": r.eqd_oar_total if oar_ok else None,
                   "ntcp_percent": r.ntcp_percent if oar_ok else None,
                   "overall_days": course.overall_days_tumour,
                   "flags": {"oar_total_valid": r.oar_total_valid, "tumour_total_valid": r.tumour_total_valid,
                             "oar_saturated": course.oar_saturated, "tumour_saturated": course.tumour_saturated}}
            if any(isinstance(v, float) and not math.isfinite(v) for v in row.values()):
                raise ValueError("Non-finite LQL-Equiv output: result refused.")
            rows.append(row)
    return {"tumour": tumour, "organs": list(organs), "reference_dose": reference_dose, "rows": rows,
            **_provenance(module, descriptor)}


def maximum_dose(workspace, descriptor, tumour, organs, reference, sessions):
    """Highest dose per session over `sessions` sessions such that no organ at risk exceeds the EQD2 it receives
    with the reference schedule: the smallest of the organs' equivalent doses (each computed by LQL-Equiv)."""
    reference.check()
    r = resume(Situation(tumour, tuple(organs), reference.dose, reference.sessions, 0, reference.gap_days, sessions),
               workspace, descriptor, counts=[sessions])
    row = r["equivalent"][0]
    doses = {o: v["equivalent"]["dose_per_session"] for o, v in row["organs"].items()}
    reachable = {o: d for o, d in doses.items() if d is not None}
    limit = min(reachable, key=reachable.get) if reachable else None
    return {"reference": asdict(reference), "sessions": sessions, "organ_equivalent_doses": doses,
            "maximum_dose": reachable.get(limit), "limiting_organ": limit,
            "tumour_equivalent_dose": row["tumour"]["dose_per_session"], "planned": r["planned"],
            "rows": r["equivalent"], "options": r["options"], "scope": r["scope"]}


def resumption(workspace, descriptor, tumour, organs, planned, done, gap_days, remaining):
    """Resumption after an interruption: the tumour-equivalent dose for the remaining sessions, each organ's
    equivalent dose, and the highest dose per session that keeps every organ within its planned EQD2."""
    planned.check()
    counts = list(range(max(1, remaining - 2), remaining + 1))
    r = resume(Situation(tumour, tuple(organs), planned.dose, planned.sessions, done, gap_days, remaining),
               workspace, descriptor, counts=counts)
    for row in r["equivalent"]:
        doses = {o: v["equivalent"]["dose_per_session"] for o, v in row["organs"].items()}
        reachable = {o: d for o, d in doses.items() if d is not None}
        row["limiting_organ"] = min(reachable, key=reachable.get) if reachable else None
        row["maximum_dose"] = reachable.get(row["limiting_organ"])
    return r


def minimum_organ_dose(workspace, descriptor, tumour, organs, reference, counts=None):
    """Same tumour effect as the reference schedule, for several numbers of sessions: the tumour-equivalent dose per
    session (LQL-Equiv) and the EQD2 it gives to each organ at risk. The best number of sessions is the one whose most
    exposed organ (relative to its EQD2 with the reference) is lowest; per organ, the number with its lowest EQD2."""
    reference.check()
    counts = sorted({n for n in (counts or (1, 3, 5, 8, 10, 15, 20, 25, 30, 35, 39, reference.sessions))
                     if 1 <= n <= 60})
    r = resume(Situation(tumour, tuple(organs), reference.dose, reference.sessions, 0, reference.gap_days, max(counts)),
               workspace, descriptor, counts=counts)
    rows = [row for row in r["equivalent"] if row["tumour"]["dose_per_session"] is not None]
    if not rows:
        raise ValueError("No number of sessions reaches the reference tumour effect within the search bound.")

    def worst(row):
        values = [v["difference_with_tumour_schedule_percent"] for v in row["organs"].values()]
        return max(v for v in values if v is not None) if any(v is not None for v in values) else math.inf

    best = min(rows, key=worst)
    per_organ = {o: min((row for row in rows if row["organs"][o]["eqd2_with_tumour_schedule"] is not None),
                        key=lambda row: row["organs"][o]["eqd2_with_tumour_schedule"], default=None) for o in organs}
    return {"reference": asdict(reference), "rows": rows, "best_sessions": best["sessions"],
            "best_dose": best["tumour"]["dose_per_session"], "best_worst_percent": worst(best),
            "per_organ": {o: (row["sessions"] if row else None) for o, row in per_organ.items()},
            "planned": r["planned"], "options": r["options"], "scope": r["scope"]}


def names(workspace):
    """Names of the library's organs and tumour sites in the ontology: {"organ"|"tumour_site": {name: [labels]}}."""
    from rdflib import Graph
    from rdflib.namespace import SKOS
    graph = Graph().parse(Path(workspace) / "ontology" / "lqlequiv.ttl")
    out = {"organ": {}, "tumour_site": {}}
    for concept, label in graph.subject_objects(SKOS.prefLabel):
        kind = "organ" if "_organ_" in str(concept) else "tumour_site" if "_site_" in str(concept) else None
        if kind:
            out[kind][str(label)] = sorted(str(a) for a in graph.objects(concept, SKOS.altLabel))
    return {k: dict(sorted(v.items())) for k, v in out.items()}
