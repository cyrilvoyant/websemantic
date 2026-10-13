# Scientific vocabulary

Definitions, units, types, categories, bounds and provenance of the parameters and outputs.

Persistent namespace: `https://w3id.org/websemantic/ns#` (prefix `wsem:`). The ontology IRI is
`https://w3id.org/websemantic/ns`; an RDF client receives [core.ttl](core.ttl), a browser this folder, and
`https://w3id.org/websemantic/ns/core/0.2.6` the version frozen at tag `v0.2.6`.

The [core](core.ttl) links software, tasks, parameters, experiments, evidence and outputs. The [TLS](tls-vocabulary.ttl),
[LQL-Equiv](lqlequiv.ttl) and [pyrcel](pyrcel.ttl) extensions declare the domain concepts. The [SHACL shapes](shapes.ttl)
check individual and relational constraints; the [competency questions](competency-questions.md) list the relations to
examine. Reading a shape is not running it: keep the traces of queries, graph checks and Python validation separate.

[LQL-Equiv definitions](../docs/lql-contract-definitions.md) · [pyrcel definitions](../docs/pyrcel-contract-definitions.md)
· [Python route](../agent/README.md)

## TLS

| File | Use |
|---|---|
| [tls-contract.json](tls-contract.json) | Complete machine contract |
| [tls-scenario.schema.json](tls-scenario.schema.json) | Configuration of one scenario |
| [tls-comparison.schema.json](tls-comparison.schema.json) | Two configurations |
| [tls-vocabulary.ttl](tls-vocabulary.ttl) | Concepts and relations (RDF, SKOS) |
| [TLS reference](../docs/tls-reference.md) | Definitions in tables |
| [Execution](../docs/agent-contract.md) | Validation and reporting |

Identifiers use `ns#tls/`. The graph links configurations, sources, versions, activities and files with SKOS and
PROV-O. The Python checks validate the configurations before the calculation.

The descriptor holds the definitions. `python tools/export_tls_contract.py` regenerates the documents. Software bounds
and qualitative conventions keep their provenance and scope.

The [qualifiers](../docs/qualificatifs.md) define parameter-specific assumptions, with source and agreement.
