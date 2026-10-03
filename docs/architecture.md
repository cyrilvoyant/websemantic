# Architecture

```
request q ──► LLM parser ──► semantic state S ──► clarification ◄──► user
                                  │
                                  ▼
                   model selection (descriptors + CodeMeta)
                                  │
                                  ▼
             execution gate G(S): SHACL shapes + rules (deterministic)
                                  │ pass only
                                  ▼
               adapter ──► unmodified simulator (pinned version)
                                  │
                                  ▼
          output annotation: JSON-LD (PROV-O, QUDT, DCAT, schema.org)
                                  │
                                  ▼
                  optional LLM explanation (reads annotated outputs only)
```

## Components

| Component | Generic? | Role |
|---|---|---|
| Descriptor | per software | Inputs (type, QUDT unit, bounds and their authority, defaults and their origin), experiment settings, outputs, supported and excluded tasks, validity domain, covered and uncovered uncertainties, entry point. Pre-filled by introspection (dataclasses, signatures, docstrings, CodeMeta, CITATION.cff), then completed by a human. |
| Adapter | per software | Converts a validated state into the native call and the native result into tabular outputs. No logic beyond mapping. |
| Semantic state | core | One record per parameter: value, unit, origin (extracted / transformed / documented profile / proposed assumption), evidence span, derivation, acceptance. Unknowns stay null; conflicts keep all candidates. |
| Parser | core | LLM with structured output. It receives only the request and the descriptor-derived schema and vocabularies. |
| Clarification | core | Questions grouped by relevance to the stated objective. |
| Selection | core | Matches the requested task to descriptors' supported tasks; refuses excluded tasks. |
| Gate | core | Structural, completeness, conflict and task-suitability checks, plus eligibility of every consumed input. |
| Annotation | core | Writes a JSON-LD record next to each output: software, version, commit, configuration, origin of every value, synthetic status, uncertainty coverage, validity domain, admitted and excluded uses. |
| Manifest | core | Request, revisions, accepted assumptions, schema and rule versions, backend commit, dependencies, LLM identity and settings, outputs. |

## Bound authority

Each bound records its authority: `code` (enforced by the simulator), `ui` (interface slider, not a physical constraint), `domain` (literature or expert), or `policy` (experimental choice). Only `code` bounds are known automatically.

## LLM integration

- Tools exposed to the LLM are generated from descriptors: `describe_model`, `propose_config`, `validate`, `run`, `annotate`.
- Transport: plain structured function calling for the prototype; MCP server optional so that any client can use it.
- No runtime code generation. No numerical value is produced outside the contract.
