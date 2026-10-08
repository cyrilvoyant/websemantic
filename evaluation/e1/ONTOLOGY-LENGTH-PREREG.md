# Ontology content and context length: preregistration

Status: preregistered 8 October 2026, before generation of any response for these
conditions. Execution belongs to Claude on the H200; this file does not launch a
campaign. Existing E1 responses are development evidence and are not reused.

## Question and estimand

Separate the effect of additional ontology content from the effect of a longer
prompt. All arms use the same native documentation, readable contract C=1, FAIR
package P=0, question, tools, output instruction and executable source versions.
This is a targeted follow-up, not a replacement of the previous 2³ factorial.

Three paired arms:

1. **Full**: unchanged complete domain ontology and shapes from the frozen E1 source.
2. **Relevant**: deterministic request-specific subset of that same graph.
3. **Relevant-padded**: byte-identical relevant graph plus non-informative padding,
   matched to the Full prompt length with the serving model's actual tokenizer.

Relevant vs Relevant-padded estimates the effect of this specific padding/length
intervention at fixed useful semantic content. Full vs Relevant-padded compares
additional semantic content at matched length. Full vs Relevant alone cannot
separate length and content. No claim about every kind of long context follows.

## Subgraph construction, before outcomes

Use only request text and frozen descriptor aliases/concept identifiers, never
reference scenarios, expected decisions or previous model answers. Exact numeric
field names and declared aliases select concepts. Add their units, quantity types,
definitions, scope and relations with one-hop dependency closure. Preserve complete
group requirements and the corresponding shapes plus their supporting declarations.
If no concept matches, include the documented task-level core, recording the fallback.
Selection rules, selected triple IDs, shape IDs, input graph hashes and resulting
text are archived before the first provider call. No case-specific manual additions
after reading results. Render RDF in a deterministic order.

A reviewer must verify before launch that the selected subset does not break a
relation by omitting its dependencies, and that its content is taken solely from
the Full arm. A smaller but incomplete graph is not an equivalent useful graph.

## Length matching and nuisance controls

Token counts, not character counts, determine matching. Freeze tokenizer revision,
chat template, full serialized prompt and truncation limit separately for each
model. Relevant-padded must equal Full in input tokens (tolerance at most one token
only if exact equality is impossible, recorded). No truncation is allowed.
Use a fixed neutral padding generator with no scientific values, tasks, software
names, commands or output-format directives. Seed and padding hashes are fixed
before launch. Its position is after the semantic block and before the question,
identical across all requests. Annotate it as irrelevant context in every arm's
common instruction. Padding can have an attention effect of its own: report it as
a limitation, not a pure physiological token-count effect.

Freeze evidence that each serving configuration accepts the largest prompt plus
the output budget; preflight rejection is an availability outcome, never a shorter
replacement prompt. Prompt materialization and token matching need their own local
tests before generation.

## Cases, models and acquisition

Use the 72 unique first turns of the frozen original pilot/qualifier corpus (TLS28,
LQL23, pyrcel21), not the later extension. Both H200 models retain their previously
declared versions/settings, three repetitions per arm. Target: 72 ×3 arms ×3
repetitions ×2 models =1296 new responses. Temperature and decoding modality are
held fixed; no historical response imported. Record exact scenario groups and
near-paraphrase dependencies in the manifest before collection.

Randomize arm order within request/repetition with a published fixed seed. Fresh
stateless calls; same system instructions, tools and output budget. Record attempts,
network/preflight failures, extraction mode, output tokens and latency. Any retries
retain their original assignment and complete trace. Failures stay in denominators.

## Endpoints and analysis

Primary: versioned scientifically valid first-turn interpretation (decision, all
required canonical values/declared unit aliases when execute, no unsupported or
unaccepted assignment). Freeze scorer version, rules and references before calls.
This endpoint does not certify autonomous execution. Unsupported reference scopes
are identified before acquisition and reported separately, not dropped after results.

Secondary: premature execution, qualifier handling, format failure, unit errors,
availability, latency and output size. Do not combine physical quantities in one
RMSD. Any numerical replay is conditional, qualified and reported separately.

Average repetitions within unique request/arm. Report paired differences and
improved/unchanged/worsened counts by domain and model. Primary contrasts are
Relevant vs Relevant-padded and Full vs Relevant-padded, two per model. Report all
four, two-sided Wilcoxon signed-rank with zero handling stated; Holm correction
over the four primary contrasts. Keep domain effects descriptive, with equal-domain
weighted summary as a sensitivity check. Scenario-family dependence remains a
limitation; a grouped/sign-based robustness analysis must not treat repeated
outputs as independent observations. No endpoint or contrast selected after outcome.

## Launch gate

Claude records the final frozen source/corpus/scorer/tokenizer hashes, verifies
subset dependencies and all length checks, and writes GO in the tri-log before
generation. This gate verifies the implementation of the approved experiment; it
is not a new request for user permission. Deviations are dated before acquisition
or reported explicitly afterwards. Original backend repositories stay unchanged.
