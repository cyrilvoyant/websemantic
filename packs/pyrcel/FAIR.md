# FAIR and FAIR4RS coverage of this pack

| Principle | Software (FAIR4RS) | Data produced (FAIR) |
|---|---|---|
| Findable | `codemeta.json`: name, repository, licence, pinned revision, link to this pack | `variables.csv` and `outputs.csv`: stable names linked to ontology concepts |
| Accessible | original repository URL and pinned revision; pack readable without any account | outputs written as CSV + JSON manifest; units and meanings in plain files |
| Interoperable | `ontology.ttl` (OWL, PROV-O, SKOS, QUDT alignment) and `shapes.ttl` (SHACL) | every unit and quantity kind as a QUDT IRI (`units.csv`); exact conversions declared |
| Reusable | `LLM-CONTRACT.md`: task scope, refusal rules, acceptance of assumptions | defaults and qualitative conventions with their authority; aggregation, temporal support and validity flags of each output |

References: Wilkinson et al., Scientific Data 3, 160018 (2016); Barker et al., Scientific Data 9, 622 (2022).
