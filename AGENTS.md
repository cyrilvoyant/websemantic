# Scientific execution contract

Read [LLM-CONTRACT.md](LLM-CONTRACT.md) first (rules, units, qualitative conventions for the three software).

Start with llm.md and agent/README.md for web-file execution without Git. Select agent/files.json (TLS), files-lql.json or files-pyrcel.json; each lists sources, hashes and dependencies. Use python agent/run.py MODEL scenario.json with an explicit accepted scenario. Read the corresponding definitions and descriptor; docs/agent-contract.md gives the detailed TLS workflow. TLS meanings are documented in docs/tls-reference.md, ontology/tls-contract.json and ontology/tls-vocabulary.ttl; LQL and pyrcel definitions are in docs/lql-contract-definitions.md and docs/pyrcel-contract-definitions.md. The TLS scenario schema is ontology/tls-scenario.schema.json.

- Never modify original simulator sources or Git repositories under external/. Only reviewed WebSemantic adapters call their pinned APIs.
- Do not invent missing values. Distinguish provided values, deterministic conversions, sourced assumptions and unknowns. A default is a proposal, not user acceptance.
- Preserve canonical units, exact categories, sources and explicit acceptance. Geography and qualitative descriptions do not determine numerical parameters automatically, except for an explicit descriptor qualitative_scale: apply that declared convention as a sourced, unaccepted assumption, never as a measurement. Explicit numeric instructions remain authoritative.
- Use the Python validation gate and approved adapter; RDF and JSON Schema alone do not authorize execution.
- For the general-agent experiment, retrieve the required source files and selected pinned backend, read its contract, construct the requested explicit accepted scenario, and execute the reviewed Python entry point or your script using the same validator and adapter. No PowerShell application or Gemini key is required. The complete example JSON illustrates the format; it is not a precomputed answer. Internal replay utilities are development checks, not the user-facing comparison workflow.
- Read actual CSV files and manifest.json before reporting results. State units, period, aggregation, synthetic origin and limitations. If execution is unavailable, say so and do not fabricate results.
- For numerical comparisons, retain software revisions, seeds, time grid and configuration. A comparison executes exactly two separately validated scenarios, with identical controlled experiment fields. Preserve each native run and qualify concatenated CSVs by scenario; do not pool samples across scenarios.

After changes to files listed in agent/files.json, regenerate its hashes with python tools/export_agent_files.py. After changes to the descriptor or output metadata, regenerate published definitions with python tools/export_tls_contract.py and check python -m pytest -q plus python -m ruff check src tests tools. Do not commit API keys or private distribution archives.
