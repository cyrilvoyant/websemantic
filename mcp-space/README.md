---
title: WebSemantic MCP
emoji: 🔺
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: 6.30.0
app_file: app.py
pinned: false
license: mit
short_description: MCP tools so agents compute with pinned scientific codes
---

# WebSemantic — MCP server

Free MCP server for language-model agents (Claude, ChatGPT, Cursor, any MCP client). The agent reads the user's
words; this server checks the scenario, and only the pinned original codes compute. No language model runs here and
no key is needed.

- **Endpoint (streamable HTTP):** `https://cyrilvoyant-websemantic-mcp.hf.space/gradio_api/mcp/`
- **Tools:** `get_contract` (read first: parameters, units, defaults, conventions, example scenario),
  `check_scenario` (decision execute / clarify / refuse with every issue; SHACL shapes for LQL-Equiv),
  `run_scenario` (computes only an accepted scenario; returns indicators, manifest with versions and SHA-256, files).
- **Codes:** TLS v1.0.1 (commit 748e053), road-tunnel electricity demand; LQL-Equiv v3.0.0 (commit dfc9a33),
  radiotherapy dose equivalence, fictitious scenarios for research and teaching, not a medical device.

Client configuration (example):

```json
{"mcpServers": {"websemantic": {"url": "https://cyrilvoyant-websemantic-mcp.hf.space/gradio_api/mcp/"}}}
```

Web app for humans: https://cyrilvoyant-websemantic.static.hf.space · Source and documentation:
https://github.com/cyrilvoyant/websemantic (folder `mcp-space/`) · MIT licence.
Built from the same `bundle.zip` as the web app (descriptors, validator, ontology, pinned codes).
