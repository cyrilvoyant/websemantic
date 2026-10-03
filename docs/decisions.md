# Decision log

| Date | Decision | By |
|---|---|---|
| 2026-10-03 | Frame the study before developing; protect the published, deployed TLS. | Cyril |
| 2026-10-03 | No measured data: synthetic benchmark; simulator outputs are computational references only. | Cyril, Codex |
| 2026-10-03 | No external EO case study (not the authors' study, no data or code). Semantic-web angle; Earth Intelligence kept as positioning and perspective only. | Cyril |
| 2026-10-03 | The approach must be software-agnostic and applicable to any new project. | Cyril |
| 2026-10-03 | Original repositories are never modified, neither locally nor on GitHub, and their deployments (Streamlit, stlite) are untouched. A new dedicated repository carries the semantic layer. | Cyril |
| 2026-10-03 | Original software is linked as pinned git submodules, not copied. | Cyril, Claude |
| 2026-10-03 | Cases: TLS (development), LQL-Equiv and pvlib (held-out). pvlib is used unmodified as a pinned dependency (BSD-3-Clause) and restricted to declared task profiles. | Cyril, Claude |
| 2026-10-03 | Co-authors: H. El-Houari, D. Julian, N. Fichaux. | Cyril |
| 2026-10-03 | Core frozen after TLS (`core-frozen` tag) to test genericity. | Claude, pending Codex |

Open questions: Nicolas Fichaux affiliation and ORCID; MCP or plain function calling; first pvlib profile (`ModelChain` or a simpler chain); target journal.

## 3 October 2026 — PoC clarification and planned measurements

Cyril confirms the PoC discussion and requests its recording. Current status: scaffold and design; the end-to-end chain is not yet implemented. The research requires comparative evidence beyond a successful example, not a production-ready product.

Record five measurement families: parameter fidelity, unsupported values, execution/clarification/refusal decisions, correct and complete output qualifications, and integration cost after core freeze. Add downstream energy/peak deviations as computational consequences, not field validation. Start with a 20–30-request TLS pilot; retain separate provenance and relational ablations for attribution. References require human review. No benchmark performance or usability gains have yet been measured.

## 3 October 2026 — First local implementation

Cyril explicitly authorises updating the manuscript, checking Git and starting the prototype. A first canonical-value validation gate and contract tests are added locally. Positive duration, step and realisation count and non-negative seed are descriptor policies, not inferred backend guarantees. No LLM, conversion, SHACL, annotation or execution wrapper yet. Exact declared-task matching is provisional. The full suite passes 21 tests, including two backend smoke tests; these are software checks, not benchmark results. Requirements used for verification are recorded in requirements-tested.txt. Existing simulators and public deployments are unchanged. No commit or push is made in this step; core-freeze remains future work.
