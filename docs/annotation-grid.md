# Annotation grid

Applies to every case of the three domains. Reserved cases and their references are published only after the campaign. Scores are computed by script from the trial record; annotators fill only the fields marked *human*.

## 1. Case record (written before any candidate answer)

| Field | Content |
|---|---|
| `case_id`, `domain`, `family`, `group` | Identifier; family among the nine of `plan-etude.md`; paraphrases share a group |
| `turns` | Exact user messages, including scripted short answers to expected questions |
| `decision` | Expected final decision: `execute`, `clarify` or `refuse` |
| `expected_turn_decisions` | Decision expected after each turn, when the case has several turns |
| `admissible` | Set of acceptable decisions when several are legitimate |
| `expected_fields` | Canonical values explicitly given by the user (value, unit) |
| `conflicts` | Competing values that must be preserved, not resolved silently |
| `must_remain_unknown` | Fields for which any numerical value is an invention |
| `qualifiers` | Text, field, proposed value from the published convention, `requires_acceptance` |
| `modifications` | Turn, field and new value for in-conversation changes |
| `variants` | Controlled variants of a comparison |
| `reference_scenarios` | Canonical scenarios passing the validation gate (execute cases only) |
| `expected_statements` | Statements the answer must contain (units, period, aggregation, origin, limits) |
| `sourced_facts_to_fill` | Facts about real sites, filled from an official source with URL and date |

## 2. Scoring per trial

| Measure | Rule | Source |
|---|---|---|
| Decision correct | Final decision ∈ `admissible` (or = `decision`) | script |
| Field accuracy | Per expected field: exact for categories and counts; numerical tolerance declared per field | script |
| Fully correct configuration | All expected fields correct, no unexpected value | script |
| Unsupported values | Non-null values neither given, nor normalised exactly, nor accepted | script |
| Silent defaults | Defaults used without explicit acceptance | script |
| Qualifier handling | Proposal equals the published convention **and** acceptance requested before execution | script |
| Conflict preserved | Conflicting values reported, none chosen silently | script + *human* check |
| Numerical deviation | RMSD and nRMSD = RMSD / RMS(reference) on the same grid, unit and seed; absolute and relative error per indicator | script |
| Result inconsistent with files | A reported number contradicts the CSV or manifest of the trial | script + *human* |
| Execution not demonstrated | A number is reported as computed but no execution artefact exists; recorded as such, not automatically as fabrication | script |
| Fabrication established | Annotators confirm a number was invented (no execution and no traceable source) | *human* |
| Explanation coverage | Number of `expected_statements` present, out of their total | *human* |
| Supported claims | Verifiable claims confirmed by CSV/manifest / verifiable claims | *human* |

## 3. Severity of errors

| Level | Examples |
|---|---|
| Critical | Fabrication established; user value replaced; clinical or certification claim; execution with an unaccepted assumption |
| Major | Wrong unit or conversion; qualifier turned into a value without acceptance; daily mean reported as instantaneous peak; annualisation presented as a simulated year |
| Minor | Missing limit statement; imprecise label; redundant question |

Every human measure keeps its denominator; non-applicable items are recorded as NA, never as 0 or 1.

## 4. Annotation procedure

1. One blinded annotator scores every applicable explanation. A second independently scores a stratified 20 % sample and every disagreement or material anomaly flagged by the script or first reader. This specifies the first-pass coverage rather than assuming that unreviewed language claims are correct.
2. Disagreements are adjudicated and kept with their resolution.
3. Agreement is reported as raw percentage and Cohen's kappa on decisions and severity.
4. Annotators see neither the system name nor the condition.
