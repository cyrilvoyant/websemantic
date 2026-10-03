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
