# Preregistration — generic clarification policy (9 October 2026, before any answer)

Requested by Cyril after the external reviews and their synthesis: isolate what the code-specific content of the
contract adds beyond a generic instruction to ask before calculating. To be checked independently.

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

## Addition recorded on 15 October 2026 (after the main analysis)

The generic-rules condition G was also collected for `gemini-3.5-flash-lite` on 15 October 2026
(`runs/e1/gemini-3.5-flash-lite__generic-20261015`, 234 answers, 0 network or HTTP error, 28 unreadable answers),
so that the figure of the contract stages has no untested cell. This collection is post hoc: it was decided after the
main analysis and is not part of the preregistered family. Contexts and instructions are byte-identical to those used for
the other models on 9 October (G contexts f3a899fd1212, 202b16d76f21, ce123472d4ed; instructions 9f8e8d33b7fc). Gemini
stays outside the Holm family of the four primary tests; the rows of the other three models in `e1-generic.csv` are
unchanged.
