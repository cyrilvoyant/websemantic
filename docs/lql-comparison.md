# Comparing fictitious schedules

`python agent/run.py lql examples/lql-comparison.json`

The document contains `task: "compare_schedules"` and `schedules`, a list of two or more schedules. Each item has a
unique `id` and a complete `scenario` in the format of `examples/lql-complete.json`. All schedules pass the validator
before the first calculation. The organ at risk and the reference dose must be identical; each value keeps its unit,
origin, source and agreement.

Without another selection, the target must be identical. For several targets, add `targets`, a parameter record whose
`value` is a list of exact library names, with `unit` set to `null`, `origin` to `assumption`, a `source` explaining
the selection and `accepted` set to `true`. For a group, replace `targets` with `anatomical_group`, with the same
structure and a descriptor key (`thoracic`, `head_and_neck`, `central_nervous_system`, `pelvis`, `abdomen`, `skin`).
The group selects the targets, never the organ at risk. A group without a target is refused.

`indicators.csv` keeps one row per schedule and target. `comparisons.csv` contains each pair for each target:
`left_dominates`, `right_dominates`, `equivalent`, `tradeoff` or `indeterminate`. TCP and NTCP differences are in
percentage points, left minus right. Dominance requires a TCP greater than or equal and an NTCP lower than or equal,
with at least one strict inequality. A missing probability forbids a verdict; no global ranking of targets is built.

The manifest keeps the accepted document, the definitions and the paths of the individual calculations, with their
native parameters, validity flags and semantic traces. This comparison of fictitious simulations is not a clinical
recommendation.
