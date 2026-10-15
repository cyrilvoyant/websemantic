# Analysis plan — numerical consequence of the first answers (15 October 2026)

Complementary analysis, post hoc with respect to the campaign: written after the campaign and after the blind human
annotation, before any recalculation of the main-campaign answers. Design reviewed by Codex (trilog, 15 October 2026).
No new language-model call; the pinned codes recompute the configurations already returned.

**Why.** The decision indicators measure compliance with the acceptance rule; two physicists judged most calculations
counted as premature acceptable. This analysis measures the numerical consequence of the configurations proposed in the
first answer. A first answer delivers no result to a user: the recalculation measures the consequence of the proposed
configuration, not a result shown to anyone.

**Inventory (frozen).** First answers of the main campaign: Mistral-Small and Qwen (`20261008T085744Z-full`), Codestral
(`final-20261008`); contexts F000 (native documentation) and F010 (documentation + contract); three repetitions; the 60
pilot requests. File list with SHA-256: `evaluation/e1/numeric-consequence-inventory.csv` (`tools`: `inventory` mode of
`evaluation/e1/numeric_consequence.py`).

**Requests with a numerical reference (numeric set).** Pilot requests whose expected first decision admits `execute`,
whose reference depends on the first turn only, and, for pyrcel, with a single aerosol mode: TLS 8, LQL-Equiv 5,
pyrcel 5 (18 requests). Qualifier requests have no unique numerical truth and are not given one. All other requests
(clarification or refusal expected, references that include later turns, several aerosol modes) appear in the decision
table only.

**Category of each answer in the numeric set** (every answer kept, same rules in both contexts):
unparsed; justified abstention (clarify or refuse when admissible); unjustified abstention (clarify or refuse when only
`execute` is admissible); incomplete configuration (`execute` with an expected field missing); invalid configuration
(non-integer count, wrong or unverifiable unit, configuration rejected by the code); technical failure (failure not due
to the candidate, such as a reference run failing); different support (the configuration simulates another period or
time step than the reference, so its outputs are not compared); comparable calculation, split into *without completion* and *with
authorised completion* (fields outside the expected set, such as protocol settings or defaults accepted by the request,
taken from the case and listed). Non-replayable answers are never coded as an error, zero or infinite.

**Primary outputs (fixed).** TLS: total energy `total_mwh` (MWh; median over the Monte Carlo realisations of the run).
LQL-Equiv: equivalent dose of the organ at risk `eqd_oar_total` (Gy; a code output, not a clinical decision). pyrcel:
activated droplet number `Nd` (cm⁻³). All other outputs compared by `numeric_e1.py` are secondary (RMSE for aligned
series, absolute error for scalars, relative error only for a non-zero reference).

**Error.** Absolute error of the primary output in its unit; relative error = absolute error / |reference| when the
reference is not zero. Numerical reproducibility: each reference configuration is run twice and the difference reported.
No tolerance threshold is used for the primary analysis.

**Aggregation and statistics.** Unit: the request. For each request and context, the median absolute error over the
comparable answers (three models × three repetitions); a request enters the paired contrast only if it has at least one
comparable answer in both contexts. Reported per code: coverage table over all answers of the numeric set; number of
paired requests; median errors; differences F000 − F010; number of non-zero differences and ties. Wilcoxon signed-rank
test (zero differences reported) per code only with at least six non-zero differences, Holm-adjusted over the codes
tested; otherwise descriptive only. No test pools codes (incompatible units). With 5 to 8 requests per code, power is
low: conclusions are conditional on the comparable subset and stated with their counts. Per-model results are
descriptive.

**Reporting.** Results reported whatever their direction, with the coverage table, so that losses of comparable answers
are visible.
