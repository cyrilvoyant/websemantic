# Preregistration — generic clarification policy (9 October 2026, before any answer)

Requested by Cyril after the external reviews and Codex's synthesis: isolate what the code-specific content of the
contract adds beyond a generic instruction to ask before calculating. Written by Claude; to be checked by Codex.

**Condition G.** Native documentation + the generic clarification policy: the six "Rules" of the frozen contract
(identical for the three codes), without their pointers to code-specific tables, units and scope, and without the JSON
rule already in the common instructions (`run_e1.generic_policy()`, derived from the frozen file, about 0.3k tokens).
G contains no unit table, no qualitative convention, no default value and no code-specific scope.
The common instructions (sha256 prefix 9f8e8d33b7fc) already state that "execute" requires every value to be
supported or accepted; G makes the generic rules explicit, the contract adds the code-specific content.

**Material.** Campaign corpus (78 requests, 72 distinct first turns), three repetitions, first turn only. Models:
Mistral-Small 3.2 24B and Qwen2.5-72B on the H200 (same serving as the campaign), Codestral online (descriptive).
F000 and F010 are the campaign answers (contexts identical by hash).

**End points and tests.** Request level, same unit as `request_level.py`. Primary: premature execution, three codes
pooled, paired Wilcoxon signed-rank (zero differences discarded): G vs F000 (does a generic policy help?) and F010 vs G
(does the code-specific content add to it?); Holm correction over these four tests (two contrasts, two open models).
Secondary, descriptive: correct decision, qualifier handled, hallucination indicators; per code; Codestral.

**Interpretation.** F010 better than G: the code-specific content (units, conventions, scope) matters beyond a generic
rule. G better than F000 and not different from F010: most of the gain comes from stating generic rules. A
non-significant difference is not equivalence. G is shorter than the contract; length is not matched.

**Paper.** One column in the table of cell means and two sentences in the contract section; no new section.
