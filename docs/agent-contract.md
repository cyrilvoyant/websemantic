# Running TLS from an agent

## Access

Start with [agent/README.md](../agent/README.md). The file `agent/files.json` lists the sources and their
fingerprints. Read the files with web tools, then write them at the given paths in the Python workspace. This route
needs numpy, pandas and rdflib; neither the project nor Git has to be installed.

The adapter checks the fingerprint of the TLS module it runs, with CRLF/LF normalisation, and records the method in
the manifest. When a checkout is present, Git checks are added. File-based provenance describes a module that matches
the published revision, not an authenticated checkout.

## Contract

Read `ontology/tls-contract.json`, `docs/tls-reference.md`, `descriptors/tls/descriptor.yaml` and the adapter
`src/websemantic/adapters/tls.py`. The scenario format is defined in `ontology/tls-scenario.schema.json`;
`examples/tls-complete.json` shows an accepted configuration.

- Keep the names, types, units and categories of the contract.
- Separate provided values, conversions, assumptions and unknowns.
- Tie each provided value to an excerpt of the request; document conversions.
- Accept a default or an assumption only after explicit agreement. A question or a negation is not agreement.
- Use the declared qualitative scales as simulation conventions. An explicit value takes priority; an ambiguity calls
  for a question.
- Keep the URL, date and justification of every source consulted. A municipality, the ambient air or road accidents
  do not determine the probabilities of TLS events.

## Calculation

Apply `websemantic.core.validation.validate`, then call the approved adapter. It checks the constraints and the TLS
revision `748e053e129669cf3e896d381e3c0ac01c763edd`. Keep the backend intact and run its calculation; explanatory
formulas do not replace it. No Gemini key is needed for this Python access.

Base seed: 42 unless explicitly requested; seed per realisation: `base_seed + run`. Keep the script, the environment,
the traces and the WebSemantic revision.

For two scenarios, validate each configuration and keep the same start date, duration, time step, number of
realisations and seed. `websemantic.comparison.run` runs both cases; `ontology/tls-comparison.schema.json` describes
their format.

## Reporting

Read the CSV files and `manifest.json`, in particular `output_qualification.tables`, before answering. Give the main
results, units, period, assumptions and folder in the user's language. The JSON repeats the computed values, their
aggregation and the revisions.

- `kpis.csv`: indicators per realisation; the medians come from these rows.
- `representative.csv` and `daily.csv`: realisation 0; daily energy in kWh, mean power in kW.
- `envelope.csv`: hourly quantiles across realisations.
- `season_profiles.csv`: profiles of the seasons covered.

`annualized_mwh = total_mwh × 365/n_days` is an extrapolation in MWh per year. `specific_kwh_m_year` is in kWh per
metre and year, all tubes included. Timestamps carry no declared time zone. The outputs are synthetic; the Monte Carlo
quantiles describe the simulated mechanisms.

A completed comparison has a `complete` manifest, two `scenario_runs` and no `INCOMPLETE.txt`. The merged CSV files
carry `scenario`. `comparison.json` gives the differences of medians and the percentage relative to scenario 2 (`null`
when the reference is zero). Common seeds do not guarantee the same draws when the parameters change their sequence.

## Maintenance

`python tools/export_tls_contract.py` regenerates the contract, vocabulary, reference and example from the descriptor.
The command runs a small scenario to list the columns.

## Short answer

By default, show the three medians (total energy, annualised energy, peak), their units, the period and the link to
the files. Add briefly "simulation; annualisation extrapolated". Keep parameters, assumptions, sources, fingerprints,
versions and seeds in the traceability files. Give details on request. If the route executed differs from the planned
route, say so in one sentence and record the details in the execution note.

## Place and context

If a city is named, consult local sources with the agent's web tools. `geography` in the contract gives the catalogue
of places, URLs, proposed fields and rules used by the local dialogue. For another place, look for suitable sources.
Record URL, date, facts consulted and assumptions in `geographical_context.json` with the results.

Keep the explicit characteristics of the tunnel. For "the same tunnel", keep its configuration; propose justified
local adaptations separately and ask for their acceptance before applying them. A city determines neither the geometry
nor the event probabilities. If sources are missing, keep the accepted assumptions and say so briefly. The simulated
date sets the seasonal factor; the city name alone does not change the TLS calculation.

## Follow-up and comparison

The detailed route is in [agent/README.md](../agent/README.md). The launcher accepts two complete scenarios and uses
the same orchestrator as the local dialogue. For a follow-up study, `--previous` keeps the link to the manifest and
records the differences; internal step, realisations and seed change only on explicit request. Keep the relevant
requests in `request`, so that the evidence stays exact; never invent quotations.

A known place named in the request requires a context provided by the agent through `--context`. For another place,
also use `--place`. The agent does the research with its web tools; the launcher checks the fields and the acceptance,
then keeps the report. These checks do not prove that the sources are true. The format is described in
`agent/context.schema.json`.
