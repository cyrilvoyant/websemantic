# Contributing

Bug reports, questions and proposals are welcome as GitHub issues. Pull requests are welcome; please open an issue
first for a large change.

## Before a pull request

```bash
python -m pip install -e ".[dev,tls,atmosphere]"
python -m pytest
python -m ruff check src
```

All tests must pass and `ruff` must report no error on `src/`. A new function or behaviour comes with a test in
`tests/`; a fixed bug comes with a regression test.

## Descriptors are the single source

Contracts, ontology extensions, SHACL rules and FAIR tables are generated from `descriptors/`. After changing a
descriptor or `ontology/core.ttl`, regenerate and check:

```bash
python tools/build_semantic_pack.py
python tools/export_agent_files.py
python evaluation/run_relational_controls.py
```

A change to the ontology bumps `owl:versionInfo` and `owl:versionIRI` in `ontology/core.ttl`, and the release is
tagged `vX.Y.Z` so that `https://w3id.org/websemantic/ns/core/X.Y.Z` resolves to it.

## Scope

The original scientific codes (TLS, LQL-Equiv, pyrcel) are used unchanged at pinned revisions; corrections to them go
to their own repositories. Evaluation cases and raw model answers stay private until a campaign closes.

## Licence

Contributions are accepted under the licence of the repository (PolyForm Noncommercial 1.0.0).
