# Architecture

Request → scenario state → validation → adapter → pinned code → results.

| Component | Role |
|---|---|
| Descriptor | Definitions, units, categories, constraints, defaults and presentation |
| Interpretation | Extract values and actions from the dialogue |
| Session | Keep the evidence, assumptions, agreements and changes |
| Validation | Check completeness, types, units, conflicts and acceptance |
| Adapter | Check the revision and call the unmodified backend |
| Export | Write CSV, JSON qualification and RDF provenance (SKOS, PROV-O) |

Every number comes from the simulator. Pages consulted serve as documentary sources. Physical assumptions require
agreement; the fixed seed follows the technical policy of the descriptor.

A comparison keeps two sessions and applies changes atomically. The controlled fields are identical; the two calls stay
separate. The merged CSV files keep the scenario identifier and the links to the native outputs.

The web app follows the same chain in the browser: a relay sends the words and the contract to the language model,
which returns variables only; the glue, the validator and, for LQL-Equiv, the SHACL shapes check the scenario before
the pinned code runs ([webapp/](../webapp/)).
