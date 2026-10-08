# Preregistration — ToolRosella baseline and blind human evaluation (8 October 2026)

Written before any ToolRosella output is used and before any human annotation. Implemented by Claude, to be reviewed
by Codex; launch decided by Cyril.

## A. ToolRosella baseline (real code)

**Why.** Reviewers will compare the contract with automatic repository-to-tool conversion. ToolRosella
(Di et al., arXiv:2603.09290) is the closest published method; a home-made imitation would not be a fair comparison.

**Material.** ToolRosella at commit 20f57dd944ba95175451cd2305a34a817e44354b (no licence: cloned for this comparison
only, kept private, not redistributed; decision of Cyril). Generator: Qwen2.5-72B-Instruct served locally by vLLM on
the H200 (same settings as the campaign); the original paper used a commercial model, so conversion rates may differ.
Codes at the campaign revisions: TLS 748e053, LQL-Equiv-web dfc9a33, pyrcel 977e909 (pre-placed sources).
Script: `hpc/run_toolrosella.sh`; tool lists exported as an MCP client sees them: `hpc/export_mcp_tools.py`.

**Recorded as results.** For each code: conversion success or failure (ToolRosella's own criterion: the generated
service starts and passes its tests), number of tools, logs. A failed conversion is reported, not retried by hand.

**Conditions (first-turn interpretation, same harness, instructions and corpus as the campaign).**
- T: native documentation + ToolRosella tool list.
- TC: T + contract (frozen campaign contract).
Compared with F000 (native documentation) and F010 (contract), already collected. If ToolRosella fails on a code, the
tool list of that code is empty in T/TC and the failure is reported.

**End points and tests.** Request level, same unit as `request_level.py`. Premature execution (primary), correct
decision, qualifier handled. Paired Wilcoxon, three software pooled, per model: T vs F000, TC vs T, TC vs F010.
Holm correction on the six primary tests (three contrasts, two models). Per-software results descriptive.

**Interpretation.** T better than F000: the interface helps. TC better than T: the contract adds what the interface
lacks (units, conventions, clarification). TC not different from F010: the interface adds nothing beyond the contract
for first-turn interpretation. No claim on execution success, which ToolRosella targets and this study does not test.

## B. Blind human evaluation

**Why.** The scorer is automatic; agreement with human judgement must be shown.

**Sample.** Stratified random sample, seed 20261008: 144 answers = 3 models (Mistral-Small, Qwen, Codestral)
x 3 codes x with/without contract (F010 vs F000) x 8 requests, drawn from requests with a non-ambiguous expected
decision. Model, condition and automatic scores are hidden; order is shuffled; a separate key file links back.

**Annotators.** Two people with the relevant expertise (Cyril, and a second annotator chosen by Cyril), independently,
using `evaluation/human/GUIDE-annotation.md`. Language models are not annotators.

**Items per answer.** Correct decision (yes/no/unsure); premature execution (yes/no); qualitative term handled
(yes/no/not applicable); wrong unit or value (yes/no); critical error (yes/no); free comment.

**Analysis.** Cohen's kappa between the two annotators and between each annotator and the automatic scorer, per item;
raw agreement; disagreements adjudicated and kept. The human-scored contract effect (F010 vs F000) is reported with
Fisher's exact test on the sample. No conclusion beyond the sample.

## Amendment recorded on 8 October 2026 after inspecting conversion failures

The initial protocol above is retained. The following changes are post-diagnostic and must not be presented as having been specified before the first conversion outputs were inspected. They do not modify the frozen factorial campaign.

- Preserve the Qwen/H200 conversion logs, including the failed environment setup and the corrected setup. Distinguish environment failures from generated-code failures.
- Evaluate an additional configuration using `hpc/run_toolrosella_local.sh`: Codestral as generator, the documented repair option enabled, and three independent workspaces per code. Keep ToolRosella and simulator sources unchanged. Record the resolved provider model identifier where available; an alias alone is not an immutable revision.
- Retain every attempt, its exit status, conversion criterion, dynamic tool export, elapsed time and available usage counters. Report successes per attempt as well as whether at least one of three attempts succeeds. Do not compare best-of-three directly with a single-attempt rate without stating the unequal budget.
- Freeze the selected tool lists and their hashes before restarting T/TC collection. Record the selection rule and selected attempt. Partial responses from different lists must not be merged. The selection rule remains to be specified before selection; this amendment does not certify that a selection has already been made.
- Report the initial and amended configurations separately. Conversion success, successful dynamic tool listing, correct entry-point coverage and successful scientific execution are distinct outcomes.
- When failed-conversion contexts are byte-identical to F000/F010 and existing answers are reused, identify them as reused observations, not new responses or independent replications. Verify context hashes and retain the same frozen instructions and requests.
- The original six primary tests concern the two open models. An additional Codestral comparison is exploratory unless a separate prospective analysis plan is recorded before inspecting those comparison outcomes. Missing conditions must not silently reduce the planned family of tests.

Interpretation clarification: a non-significant TC–F010 contrast does not establish equivalence or absence of added value. It only means that the specified test did not detect a difference on this first-turn endpoint. An unusable answer is not a successful scientific response merely because it contains no premature execution decision.
