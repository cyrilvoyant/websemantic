# Preregistration — reduced and competing semantic contexts (8 October 2026)

Written before collection of L2/L3. Implemented by Claude, reviewed by Codex.
The 8 October review narrows the interpretation without changing frozen contexts,
conditions, corpus, model settings or historical answers. This is the operational
L2/L3 protocol; `e1/ONTOLOGY-LENGTH-PREREG.md` describes a separate future experiment.

## Question

In the factorial campaign, adding the complete ontology package (O) to the contract (C) lowered correct decisions and
raised premature execution for TLS, whose O package is long (about 120k characters). Is the effect due to the
semantic context? This experiment compares whole context packages. It cannot
isolate token length, formatting, semantic relevance or attention competition.

## Conditions (all with the frozen campaign packs, commit 3e89b09, same instructions hash 9f8e8d33b7fc)

| Code | Context | Status |
|---|---|---|
| F010 | native documentation + contract | collected (campaign 20261008T085744Z-full) |
| F110 | native documentation + full O package (ontology.ttl + shapes.ttl) + contract | collected |
| L2 | native documentation + the software's own semantic content only (ontology-compact.ttl) + contract | **new** |
| L3 | native documentation + off-topic RDF of the same length and format as the full O package + contract | **new** |

Construction: `evaluation/e1/build_length_controls.py`; frozen files in `evaluation/e1/frozen-packs-3e89b09/`.
`reviewed-contexts.json` records full SHA-256 hashes. The collector verifies all
reviewed files, instructions and constructed contexts before any provider call.
The builder verifies existing reviewed artifacts instead of overwriting them.
The frozen F010 and F110 contexts were rebuilt from these files and reproduce the campaign hashes exactly
(tls aecac2766b8a / e9267dafcb35, lqlequiv 331c43d8ee98 / 358c7e67d3c6, pyrcel 62c639f42c2a / 286f0806457a).

Sizes (characters, whole context): TLS L2 121 565, L3 147 414, F110 147 452; LQL-Equiv L2 39 676, L3 61 730,
F110 61 686; pyrcel L2 28 654, L3 50 416, F110 50 476. For TLS the compact content is still 78 % of the full package
(the TLS vocabulary is mostly its own concepts), so for TLS the separation relies mainly on L3.

## Models, corpus, repetitions

Qwen2.5-72B-Instruct and Mistral-Small-3.2-24B on the H200, same vLLM settings as the campaign (temperature 0, eager
mode, prompted JSON). Same 78 first-turn requests (pilot + qualifiers), three repetitions: 468 new answers per model.

## End points and analysis (fixed now)

Unit: unique first-turn request (same definition as `request_level.py`), repetitions averaged.
Metrics: premature execution (primary), correct decision, qualifier handled.
Paired Wilcoxon signed-rank tests at request level, three software pooled, per model:

1. **L3 vs F010** — does same-length off-topic RDF reproduce the degradation?
2. **L3 vs F110** — is full O different from same-length off-topic RDF?
3. **L2 vs F010** — does the software's own compact content help or harm?

Correct the six primary premature-execution tests (three contrasts, two models)
with Holm. Other endpoints and per-software results are descriptive. Report
request counts, paired differences and improved/unchanged/worsened counts.
Related scenario families remain potentially dependent. Repeated outputs are
not independent observations. Reused F010/F110 add a collection-batch limitation.

## Interpretation rules (fixed now)

- L3 worse than F010: competing RDF context can impair the measured task under this presentation.
- F110 different from L3: the two packages differ; this does not identify an ontology-only effect.
- L2 better than F110: the reduced package performs better for this benchmark; size and content still covary.
- A nonsignificant difference does not demonstrate equivalence. No equivalence margin is registered here.
- Character matching is not token matching. Other-domain RDF includes shared vocabulary and may distract;
  L3 is not neutral padding. Its different heading also forms part of the intervention.
- Null results are reported. No general claim about ontology usefulness or pure length effects is permitted.

## Launch and scope

GO for this contextual robustness experiment once local checks pass. Claude runs
`MODE=full CONDS_OVERRIDE=L2,L3` with a new campaign tag and the same pinned H200
models/settings. Keep every attempt, failure and response; do not replace the
historical campaign. Archive tokenizer/model revisions and token usage when
available, but do not silently truncate. Code review is not evidence that the
H200 environment or generation has succeeded. This protocol does not authorize
the separate 1296-response token-matched experiment.
