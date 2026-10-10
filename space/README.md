---
title: WebSemantic
emoji: 📐
colorFrom: gray
colorTo: gray
sdk: gradio
sdk_version: 5.38.0
python_version: "3.12"
app_file: app.py
pinned: true
license: mit
short_description: Scientific codes that ask before they compute
tags:
  - mcp-server
  - scientific-software
  - semantic-web
  - ontology
  - radiotherapy
  - energy
---

# WebSemantic — ask before you compute

Talk to two scientific codes, in English or French, by text or voice: **road-tunnel electricity demand** (Tunnel
Load Simulator) and **radiotherapy dose equivalence** (LQL-Equiv). The code asks for what is missing, proposes its
declared conventions for vague words ("a lot of traffic", "a long tunnel"), and computes only what you accepted.
Outputs come with their units, time series, a short analysis and their provenance (exact code revision, DOI,
validity limits).

How it works: a language model (Mistral) only reads each message against the code's contract. Everything after
that is local and deterministic: a validator decides (execute, clarify, refuse) and the unchanged, pinned code
computes. Scenarios are fictitious by design; do not enter personal or patient data.

**MCP server.** This Space is also an MCP server for your own AI assistant:
`https://cyrilvoyant-websemantic.hf.space/gradio_api/mcp/sse` — tools `list_models`, `get_contract`,
`validate_scenario`, `run_scenario`.

- Source: https://github.com/cyrilvoyant/websemantic (MIT) · PyPI: `pip install websemantic`
- Concept DOI: https://doi.org/10.5281/zenodo.23238902
- Ontology: https://w3id.org/websemantic/ns
- Author: Cyril Voyant, Mines Paris – PSL ([ORCID 0000-0003-0242-7377](https://orcid.org/0000-0003-0242-7377))
