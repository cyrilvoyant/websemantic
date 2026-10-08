# Preregistration — contract effect on held-out requests (8 October 2026, before any answer)

Written by Claude after Codex's review (trilog, 8 October 2026: the corpus and the scorer are built around the
contract conventions; risk that the contract fits the corpus). Launch decided by Cyril.

**Why.** The campaign corpus (78 requests) and the contract were developed together. A held-out set written after the
contract tests whether the contract effect transfers to new requests.

**Material.** The 60 extension cases (`benchmark-reserve/*/extension.jsonl`, 20 per code), written on
8 October 2026 at 14:19 (+02:00) and validated by Cyril (status `validated-cyril-20261008`); new families included
(unit traps, simulated vs measured, output units, domain traps, paraphrases, LQL comparisons and anatomical groups).
Contracts used: the current packs (`packs/*/LLM-CONTRACT.md`), last changed at 12:38 (+02:00), i.e. before the
cases were written; this contract includes the LQL comparison task and anatomical groups added after the campaign
freeze. Instructions unchanged (sha256 prefix 9f8e8d33b7fc). Native documentation unchanged (F000 identical to the
campaign by hash).

**Conditions.** F000 (native documentation) and F010 (native documentation + contract), three repetitions, single
first turn; models: Mistral-Small 3.2 24B and Qwen2.5-72B on the H200 (same serving as the campaign), Codestral
online (free tier).

**End points and tests.** Unit: unique first-turn request, repetitions averaged. Primary: premature execution,
F010 vs F000, three codes pooled, paired Wilcoxon signed-rank (zero differences discarded), Holm correction over the
three models. Secondary (descriptive): correct decision; per code; per family; LQL comparison and group cases.
The scorer is the campaign scorer (v1) without change; cases with several reference schedules are scored on the
decision only.

**Interpretation.** A lower premature-execution rate with F010 on held-out requests supports transfer of the contract
effect beyond the development corpus. No difference, or a reversal, is reported as such. No claim on execution success.
