# semantic-sim-layer

**A software-agnostic semantic layer between human intent and existing scientific simulators.**

> Status: research prototype, scaffold only (October 2026). No implementation, benchmark or result yet.
> The name is provisional.

## Purpose

Scientific software exposes numerical parameters, while users ask questions. This repository studies a generic, non-intrusive layer that:

1. turns a natural-language request into a **traceable semantic state**: every value is user-provided, deterministically transformed, an accepted assumption or unknown, and none is silently invented;
2. **selects** a suitable model and validates a configuration before any run, by checking structure, units, bounds, completeness, conflicts and task suitability;
3. runs the **unmodified** simulator;
4. **qualifies the simulated data**: each output is published as a self-describing JSON-LD record stating which software, version and configuration produced it, which assumptions were accepted, which uncertainties are and are not covered, and what uses are admitted or excluded.

The layer is agnostic. Supporting a new software only requires a **descriptor** and a thin **adapter**. The core never changes.

## Design principles

- **Non-intrusive**: target software is never modified, locally or on GitHub. TLS and LQL-Equiv are linked as git submodules pinned to exact commits (read-only references); pvlib is a pinned PyPI dependency. Only their public APIs are called.
- **Non-invention**: an unsupported value that is not an accepted assumption cannot reach the simulator.
- **LLM as interpreter, not as calculator**: the language model only sees deterministic tools generated from descriptors (`describe_model`, `propose_config`, `validate`, `run`, `annotate`). It never executes code and never computes results. Any explanation reads annotated outputs only.
- **LLM-agnostic**: one commercial API and one open local model, for reproducibility. Ranking LLMs is not a goal.
- **Standards**: QUDT for units, PROV-O for provenance, SHACL for the execution gate, DCAT and schema.org for output datasets, CodeMeta and CITATION.cff as input to model selection.

## Case studies

| Role | Software | Domain | Link | Licence |
|---|---|---|---|---|
| Development case (core built here, then frozen) | Tunnel Load Simulator (TLS) | Road-tunnel electricity demand, Monte Carlo | submodule `external/tunnel-load-simulator` @ `748e053` · [repo](https://github.com/cyrilvoyant/tunnel-load-simulator) · [DOI](https://doi.org/10.5281/zenodo.20080042) | MIT |
| Held-out case 1 (same authors, other domain) | LQL-Equiv | Radiobiology: BED, EQD2, NTCP, TCP | submodule `external/LQL-Equiv-web` @ `dfc9a33` · [repo](https://github.com/cyrilvoyant/LQL-Equiv-web) · [DOI](https://doi.org/10.5281/zenodo.21948623) | MIT |
| Held-out case 2 (third-party library) | pvlib-python | PV system modelling | PyPI `pvlib==0.16.1` · [repo](https://github.com/pvlib/pvlib-python) | BSD-3-Clause |

**Genericity protocol**: the core is developed on TLS only, then frozen with the git tag `core-frozen`. LQL-Equiv and pvlib are then integrated by adding descriptors and adapters only. Any required change to the core is logged and reported as a partial genericity failure. Integration cost is measured: descriptor and adapter lines, time, and fields auto-filled versus written by hand.

**Scope limits**:
- LQL-Equiv is research and education software, not a medical device. Individual-patient clinical requests are an *expected refusal* class.
- pvlib is restricted to declared task profiles (e.g. `ModelChain`). Requests outside a profile are refused or flagged, never improvised.
- No measured tunnel, PV or clinical data are used. Simulator outputs are computational references, not observations.

## Repository layout

```
src/semantic_sim_layer/core/      generic core: semantic state, parser, clarification, validation, selection, run, annotation
src/semantic_sim_layer/adapters/  thin per-software adapters (the only code touching target APIs)
descriptors/{tls,lqlequiv,pvlib}/ declarative descriptors (inputs, outputs, tasks, validity, entry point)
ontology/                         SHACL shapes and JSON-LD context
benchmark/                        requests, reference annotations, evaluation scripts
docs/                             architecture, protocol, decisions, context
external/                         pinned submodules (read-only, never edited)
tests/                            smoke and non-regression tests
```

## Getting started

```bash
git clone --recurse-submodules <url>
python -m venv .venv
.venv\Scripts\activate          # Linux/macOS: source .venv/bin/activate
pip install -e ".[dev,backends]"
pytest
```

The smoke test checks that TLS and LQL-Equiv still run through the submodules and reproduce a documented reference output.

## Documentation

- [docs/architecture.md](docs/architecture.md): components and data flow
- [docs/protocol.md](docs/protocol.md): benchmark, comparators, metrics
- [docs/decisions.md](docs/decisions.md): decision log
- [docs/context.md](docs/context.md): origin of the study and the remarks from the 2 October 2026 demonstration

Project governance (Cyril / Codex / Claude) is kept in `trilog.md` in the parent working folder, outside this repository.

## Authors and citation

Cyril Voyant, Mines Paris – PSL, O.I.E. ([ORCID 0000-0003-0242-7377](https://orcid.org/0000-0003-0242-7377)). The rest of the author list is to be confirmed. See [CITATION.cff](CITATION.cff).

Homepage: <https://www.cyrilvoyant.com>

## Licence

MIT for the code in this repository. Linked and dependent software keep their own licences (TLS: MIT; LQL-Equiv: MIT; pvlib: BSD-3-Clause).
