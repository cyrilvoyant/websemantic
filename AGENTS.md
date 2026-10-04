# Scientific execution contract

Read docs/agent-contract.md before preparing or running a scenario. Parameter and output meanings are documented in docs/tls-reference.md, ontology/tls-contract.json and ontology/tls-vocabulary.ttl. The canonical scenario format is ontology/tls-scenario.schema.json.

- Never modify original simulator sources or Git repositories under external/. Only reviewed WebSemantic adapters call their pinned APIs.
- Do not invent missing values. Distinguish provided values, deterministic conversions, sourced assumptions and unknowns. A default is a proposal, not user acceptance.
- Preserve canonical units, exact categories, sources and explicit acceptance. Geography and qualitative descriptions do not determine numerical parameters automatically, except for an explicit descriptor qualitative_scale: apply that declared convention as a sourced, unaccepted assumption, never as a measurement. Explicit numeric instructions remain authoritative.
- Use the Python validation gate and approved adapter; RDF and JSON Schema alone do not authorize execution.
- For the general-agent experiment, retrieve the repository and pinned TLS code, read the contract, construct the requested explicit accepted scenario, and write and execute your Python script using the reviewed validator and adapter. No PowerShell application or Gemini key is required. The complete example JSON illustrates the format; it is not a precomputed answer. Internal replay utilities are development checks, not the user-facing comparison workflow.
- Read actual CSV files and manifest.json before reporting results. State units, period, aggregation, synthetic origin and limitations. If execution is unavailable, say so and do not fabricate results.
- For numerical comparisons, retain software revisions, seeds, time grid and configuration. One scenario is executed per run.
- LQL and pvlib integrations remain work in progress. Do not imply scientific transfer or field validation has been demonstrated.

After changes to the descriptor or output metadata, regenerate published definitions with python tools/export_tls_contract.py and check python -m pytest -q plus python -m ruff check src tests tools. Do not commit API keys or private distribution archives.
