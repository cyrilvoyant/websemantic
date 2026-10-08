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
| CQ11 | Which reference fractionation defines EQD in LQL? | Declared reference dose per fraction (2 Gy unless stated). | graph | tested (`lqlequiv.ttl`) |
| CQ12 | Which inputs define a pyrcel run, and in which units? | Updraft V (m/s), initial T0 (K), P0 (Pa), S0 (supersaturation, 1), aerosol modes (N, μ, σ, κ); no default aerosol population. | graph | tested (`pyrcel.ttl`) |

| CQ13 | Are dose per fraction, number of fractions and total dose independent? | No: total is derived; disagreement = conflict | graph | tested |
| CQ14 | May a saturated EQD be reported? | No: each per-course flag invalidates the matching EQD; the global flag only signals | graph + Python flag | tested (graph, direction checked) |
| CQ15 | Does « hypofractionnement modéré » fix a dose? | No: clarification | graph | tested |
| CQ16 | Is a patient-specific request in scope? | No: refuse | rules | pending adapter |
| CQ17 | Are relative humidity and S0 independent? | No: one state, S0 = RH_fraction − 1 (conversion, not equality) | graph + SHACL | tested |
| CQ18 | In which unit is `Nd` returned? | m⁻³, while input N is in cm⁻³ | graph | tested |
| CQ19 | Does « air pollué » fix an aerosol population? | No: clarification | graph | tested |
| CQ20 | Is a rain forecast for a city in scope? | No: refuse | rules | pending adapter |
| CQ21 | Which tumour sites are « les volumes cibles thoraciques » ? | Lung, Oesophagus, Breast carcinoma (SKOS collection over library names) | graph | tested |
| CQ22 | Does an anatomical group choose the organ at risk? | No: the organ is stated or asked | graph + rules | tested (graph) |
| CQ23 | When is a schedule « meilleur » for a target? | Only if it dominates (TCP ≥ and NTCP ≤, one strict); else trade-off | graph | tested |
| CQ24 | Does « hypofractionnement modéré » give a dose per fraction? | No: always asked for LQL-Equiv | graph | tested |

Domain extensions (`lqlequiv.ttl`, `pyrcel.ttl`) add instances only; a test checks that they declare no new class. This shows reuse of the core for these two cases, not a general proof of domain independence. `derivationRule` strings are documentary; the executed checks are the SHACL shapes (`shapes.ttl`): numeric type, bounds and complete groups are generic (read from the graph, per course or aerosol-mode instance); the LQL total-dose and pyrcel RH/S0 shapes are domain-specific. Unit and quantity-kind IRIs were checked to resolve on qudt.org on 6 October 2026.

Ablation link: CQ2–CQ7 and CQ9 are the relational behaviours measured by condition B3 against B2 (flat contract with the same definitions, without relations).
