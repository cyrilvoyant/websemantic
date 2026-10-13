# Adding a code

1. Create `descriptors/<code>/descriptor.yaml`: software, parameters, experiment, tasks and presentation. Define types,
   units, categories, bounds, meanings and references.
2. Declare the defaults with their provenance. Keep `operational_default` for technical settings that are explicitly
   allowed. Describe the aliases and the unit conversions.
3. Write a local adapter `run(scenario, descriptor, workspace, output_root=None)` that returns `(folder,
   median_indicators)`. Validate, then call the unmodified backend; produce the CSV files and `manifest.json` with
   software, scenario and qualification.
4. Declare `runtime.adapter`, and the backend path and marker if needed. Register the code in
   `src/websemantic/environments.json` once it has been checked.
5. Define the tables, indicators and notes in `presentation.results`. Test configurations, refusals, units and
   provenance.

A `qualitative_scale` maps an expression to a typed value or to a fraction of a documented reference. It proposes
assumptions that must be accepted. `qualitative_policy` governs categories, dates and identifiers.

Places, sources and context rules belong to the descriptor. The code that runs comes only from the declared local
adapters. The vocabulary and the provenance are exported from the code's definitions.

Pin the code itself as a Git submodule at a fixed commit (see `.gitmodules`); WebSemantic never modifies it.
