# Competency questions

Each question states the expected answer and the mechanism that answers it: **graph** (SPARQL over `core.ttl` and exported contracts), **SHACL** (shape check), or **Python** (validation gate or normalisation). A Python check is never credited to the ontology. Graph questions are tested in `tests/test_core_ontology.py`.

| # | Question | Expected answer | Mechanism | Status |
|---|---|---|---|---|
| CQ1 | Which tasks does a software support, and which does it exclude? | TLS: tunnel demand under stated assumptions / excludes certification. LQL: fractionation equivalence / excludes patient decisions. pyrcel: adiabatic parcel activation / excludes weather forecasting. | graph | tested |
| CQ2 | Can a qualitative term fix a value without user acceptance? | No: every `QualifierMapping` has `requiresAcceptance true`. | graph + SHACL | tested (graph) |
| CQ3 | What does « beaucoup de trafic » propose in TLS? | `traffic_level = 1.5`, dimensionless, a study convention, to accept. | graph | tested |
| CQ4 | Does « fortement éclairé » map to a TLS value? | No mapping: a clarification policy applies (TLS has no illuminance parameter). | graph | tested |
| CQ5 | May an output be summed over time steps? | Step energy: yes. Power: no. | graph | tested |
| CQ6 | Is annualised energy an observed year? | No: aggregation = extrapolation 365/n_days. | graph | tested |
| CQ7 | Does a daily mean answer a question about instantaneous peak power? | No: temporal support differs (daily vs native step). | graph | to export (daily table) |
| CQ8 | Does « 2 km » map to `length_m` in m? | 2000 m, deterministic normalisation, not inference. | Python | covered by existing tests |
| CQ9 | Does a bound come from code, interface or physics? | From `ws:authority` of each bound. | graph | to export from descriptors |
| CQ10 | Does a city name justify a traffic value? | No: geography yields proposals only, never accepted values. | Python + rules | covered by existing tests |
| CQ11 | Which reference fractionation defines EQD in LQL? | Declared reference dose per fraction (2 Gy unless stated). | graph | pending LQL contract |
| CQ12 | Which inputs define a pyrcel run, and in which units? | Updraft V (m/s), initial T0 (K), P0 (Pa), S0 (supersaturation, 1), aerosol modes (N, μ, σ, κ); no default aerosol population. | graph | pending pyrcel contract |

Ablation link: CQ2–CQ7 and CQ9 are the relational behaviours measured by condition B3 against B2 (flat contract with the same definitions, without relations).
