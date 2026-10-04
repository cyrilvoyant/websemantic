# Evaluation protocol (draft)

No measured data are used. Three reference levels:

1. intended configuration;
2. admissible decision (execute / clarify / refuse);
3. simulator output on the reference configuration, which is a computational reference and not an observation.

## Corpus

- Pilot of 20–30 requests, then about 60 requests per software.
- Classes:
  - complete;
  - incomplete;
  - qualitative or ambiguous;
  - contradictory or invalid;
  - linguistic variants (register, word order, French and English);
  - out-of-scope or excluded task, e.g. individual-patient decisions for LQL-Equiv.
- Two configuration-first and intent-first subsets. Paraphrases are grouped with their parent scenario in splits.
- Two independent annotators; disagreement and adjudication are reported. Where several completions are legitimate, the reference is a set of admissible decisions.

## Comparators

| System | Components |
|---|---|
| A0 | Direct LLM configuration |
| A1 | Typed schema and controlled vocabularies |
| A2 | A1 + deterministic validation and clarification |
| A3 | A2 + provenance and assumption acceptance |
| A4 | A3 + relational knowledge, task-suitability rules and shared vocabularies |

Contrasts: A3−A2 (provenance) and A4−A3 (semantics). Same LLM, budgets and settings within a comparison; one commercial and one open local LLM.

## Metrics

- Unsupported assignment rate: unsupported non-null values / non-null values.
- Missingness precision and recall.
- Invalid acceptance (expected non-execution) and incorrect refusal (expected execution).
- Evidence accuracy, conflict preservation.
- Downstream indicator error relative to the computational reference (matched seeds and horizon).
- Repeated-call agreement (K repetitions).
- Annotation completeness of outputs: share of required provenance and qualification fields present and correct.
- Genericity: core changes after `core-frozen`, integration lines and time, share of descriptor fields auto-filled.

## Statistics

Paired comparisons; scenario-level bootstrap intervals; Wilcoxon signed-rank for paired contrasts; effect sizes reported alongside tests.

## PoC scope and operational measures (3 October 2026)

This is a proof of concept, not a complete product. The full request-to-qualified-output chain has not yet been implemented. Feasibility demonstrations must be distinguished from evidence that the semantic layer adds value. Develop on TLS, freeze the core, then attempt transfer to LQL-Equiv and one bounded pvlib task profile.

Five primary measurement families are planned:

| Family | Operational definition |
|---|---|
| Parameter fidelity | Correctly extracted explicitly specified fields / expected specified fields. Normalise units, predefine numerical tolerances, and report type-specific and scenario-level summaries. |
| Unsupported values | Unsupported non-null assignments without an accepted assumption / all non-null assignments. Report counts and undefined denominators. An accepted assumption is not an observation. |
| Decision quality | Confusion matrix for execute / clarify / refuse, missingness precision and recall, false acceptance among non-executable requests and incorrect refusal among executable requests. |
| Output qualification | Required annotation fields present and correct / required fields. Separately count omissions and false assertions, using human references and independently recorded execution manifests. |
| Transfer cost | Active integration time, descriptor/adapter additions, manually versus automatically populated fields, and number and nature of post-freeze core changes. Lines of code are descriptive, not a sufficient measure of difficulty. |

Energy and peak-power deviations against a matched TLS reference run are complementary outcomes. Use absolute error and relative error for nonzero references. For incomplete requests without an admissible reference configuration, score clarification rather than manufacture a numerical target. These deviations measure interface-induced computational changes, not accuracy against actual energy measurements.

Begin with 20–30 TLS requests to refine the protocol and references. Before the full benchmark, fix a primary outcome, numerical tolerances, interaction budgets and annotation rules. A minimal simple-versus-enriched comparison establishes whether the added layer helps; A3–A2 and A4–A3 are required to attribute provenance and relational effects separately. Score raw proposals and final accepted configurations separately.

Human-reviewed reference data include values, unknowns, conflicts, admissible decisions and correct annotations. Group paraphrases and repeated calls by underlying scenario. Report null and adverse effects as well as improvements. No usability benefit is established without an appropriate interaction study. No measured tunnel data are available or required for this interface-level evaluation.

The statistical test will be selected for the outcome and dependence structure; Wilcoxon is not automatically appropriate for binary decisions. Paired categorical comparisons and scenario-level confidence intervals may require other methods. Three integrations provide bounded transfer evidence, not proof of support for arbitrary software.

## Fixed technical setting for conversational tests

The default base seed is 42 and remains unchanged unless the user explicitly requests another value. Each Monte Carlo realization uses base_seed + run. Record both columns from kpis.csv and the configuration in manifest.json for every test. This technical setting is omitted from ordinary dialogue; changing it is an explicit experimental change, not a new physical assumption. Use identical seeds when comparing trajectories.
