# Preregistration — length control for the ontology factor (8 October 2026)

Written before any answer for L2 or L3 is collected. Proposed by Codex (trilog, 8 October), implemented by Claude,
to be validated by Codex before launch.

## Question

In the factorial campaign, adding the complete ontology package (O) to the contract (C) lowered correct decisions and
raised premature execution for TLS, whose O package is long (about 120k characters). Is the effect due to the
**semantic content** of the ontology, or to the **length and format** of the added material?

## Conditions (all with the frozen campaign packs, commit 3e89b09, same instructions hash 9f8e8d33b7fc)

| Code | Context | Status |
|---|---|---|
| F010 | native documentation + contract | collected (campaign 20261008T085744Z-full) |
| F110 | native documentation + full O package (ontology.ttl + shapes.ttl) + contract | collected |
| L2 | native documentation + the software's own semantic content only (ontology-compact.ttl) + contract | **new** |
| L3 | native documentation + off-topic RDF of the same length and format as the full O package + contract | **new** |

Construction: `evaluation/e1/build_length_controls.py`, deterministic; files in `evaluation/e1/frozen-packs-3e89b09/`.
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

Per-software results are reported descriptively (small samples).

## Interpretation rules (fixed now)

- L3 worse than F010 and close to F110: the degradation is mainly due to length/format, not to ontological content.
- F110 worse than L3: the full ontological content itself is harmful as a prompt.
- L2 not worse than F010 while F110 is worse: a compact, relevant subset is usable; the size of the full package is
  the problem.
- No conclusion is drawn from a single software or a single model; null results are reported as such.
