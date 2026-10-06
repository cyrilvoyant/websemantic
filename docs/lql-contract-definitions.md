# LQL-Equiv contract: concept definitions (draft for review)

Scope: definitions, units, bounds, qualifiers and refusal policy. The adapter, descriptor YAML and API mapping are implemented separately and must match the pinned revision `dfc9a338205b8864b8e3470c4ae245b019e88844` (API read on 6 October 2026: `Course`, `Prescription`, `Options`, `compute`, `load_library`). Scientific meaning to be reviewed by Cyril and D. Julian before activation.

## 1. Task profiles

| Profile | Status |
|---|---|
| Compare fractionation schedules with a reference fractionation: BED, EQD, NTCP, TCP, radiation-induced cancer risk, for research and education | supported |
| Prescribe, modify or validate a treatment for an individual patient | **excluded**: refuse |
| Reproduce a result published with the 2014 application (`Options.legacy_2014`) | supported only on explicit request; never the default |

## 2. Inputs

| Field | API | Meaning | Unit | Bounds (authority) | Default (origin) |
|---|---|---|---|---|---|
| `organ` | `compute(organ, …)` (1st positional) | Organ at risk from the shipped library (34 entries) | category | library names (code) | none: must be stated |
| `tumour_site` | `compute(…, tumour, …)` (2nd positional; API name `tumour`) | Tumour site from the shipped library (20 entries) | category | library names (code) | none: must be stated |
| `courses[k].dose_per_fraction` | `Course.dose_per_fraction` | Physical dose per fraction of course k | Gy (`unit:GRAY`) | ≥ 0 (code) | none |
| `courses[k].n_fractions` | `Course.n_fractions` (float in the API) | Number of fractions of course k | count | ≥ 0 (code); integer ≥ 1 (profile policy for physical schedules) | none |
| `courses[k].gap_days` | `Course.gap_days` | Interruption before course k | d (`unit:DAY`) | ≥ 0 (code) | 0 (code default) |
| number of courses | `len(Prescription.courses)` | Successive courses | count | ≤ 10 (code: `MAX_COURSES`); ≥ 1 (profile policy, the code accepts an empty tuple) | 1 |
| `reference_dose` | `Prescription.reference_dose` | Dose per fraction of the reference fractionation defining EQD | Gy | ≥ 0 (code); > 0 (profile policy: 0 is constructible but does not guarantee a computable EQD) | 2.0 (code default, proposed and stated in every answer; not a clinical default) |
| `bifractionated` | `Prescription.bifractionated` | Two fractions a day | boolean | — | false (code default) |
| `time_model`, `tcp_model`, `reproduce_2014` | `Options` | Calculation switches | category / boolean | enumerations (code) | `Options()` defaults (code) |

Derived, not independent: total dose = dose per fraction × number of fractions. If a user gives all three and they disagree, this is a **conflict** to preserve, not a value to choose. This is a relational rule (condition B3).

Tissue parameters (α/β, T½, Tk, Tp, d50, m, …) come from the library and are **not** user inputs in this profile. A request to change α/β is out of profile: clarify.

## 3. Outputs

| Output | API | Unit | Aggregation | Notes |
|---|---|---|---|---|
| BED organ / tumour per course | `CourseResult.bed_oar`, `bed_tumour` | Gy | per course | Biologically effective dose |
| EQD organ / tumour per course | `CourseResult.eqd_oar`, `eqd_tumour` | Gy | per course | Equivalent dose at `reference_dose`; always state the reference |
| Cumulative EQD | `Result.eqd_oar_total`, `eqd_tumour_total` | Gy | sum over courses | Invalid if `oar_total_valid` / `tumour_total_valid` is false |
| NTCP | `Result.ntcp_percent` | % | whole prescription | Model estimate for research; `None` when not available |
| TCP | `Result.tcp_percent` | % | whole prescription | Model estimate; sigmoid stated (`tcp_model`) |
| Cancer risk | `Result.cancer_risk` | 1 | whole prescription | `None` when the tissue has no risk coefficients |
| Saturation flag | `Result.saturated` | boolean | — | If true, the equivalent dose is a search bound and **must not be reported as a result** |

Comparisons use absolute and relative errors on one quantity at a time. BED, EQD and probabilities are never concatenated into one vector.

## 4. Qualifiers

| Expression | Field | Treatment |
|---|---|---|
| « fractionnement conventionnel », « classique » | `dose_per_fraction` | Proposal 2.0 Gy, to accept |
| « hypofractionnement modéré » | `dose_per_fraction` | **Clarification**: the user states the dose per fraction; no numerical range is proposed before sourced scientific review |
| « hypofractionnement extrême », « stéréotaxique » | `dose_per_fraction` | **Clarification**: the user states the dose per fraction; no numerical range before review |
| « hyperfractionnement » | dose / frequency | **Clarification**: the word alone does not fix two sessions a day |
| « deux séances par jour » | `bifractionated` | Explicit setting `bifractionated = true`; dose per fraction must still be stated |
| « longue interruption », « pause d'une semaine » | `gap_days` | « une semaine » → 7 d (exact conversion); « longue » → clarification |
| « dose élevée », « peu de séances » | dose / fractions | Clarification: no study convention |

Only « conventionnel » carries a proposed value (2 Gy, to accept). Any numerical convention for other expressions requires sourced review by Cyril and D. Julian before it enters the contract.

## 5. Refusal policy (task exclusion)

Refuse, and explain the research and education scope, when the request:
- names or describes an individual patient (« mon patient », « pour Mme X », age or history of a person), or
- asks whether a treatment may be prescribed, modified, continued or validated, or
- asks for a clinical decision on toxicity or tumour control.

A fictitious or textbook schedule (« un schéma 20 × 3 Gy comparé à 2 Gy ») is in scope.

## 6. Competency questions added

| # | Question | Expected answer | Mechanism |
|---|---|---|---|
| CQ11 | Which reference defines EQD? | `reference_dose`, 2 Gy unless stated | graph |
| CQ13 | Are dose per fraction, number of fractions and total dose independent? | No: total = d × n; disagreement = conflict | graph rule (B3) |
| CQ14 | May a saturated EQD be reported? | No | Python flag + graph |
| CQ15 | Does « hypofractionnement modéré » fix a dose? | No: clarification | graph |
| CQ16 | Is a patient-specific request in scope? | No: refuse | rules |
