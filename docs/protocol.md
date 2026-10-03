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
