# WebSemantic

Software-agnostic semantic layer for scientific codes (research prototype). One descriptor per code is compiled into
three documents: a readable contract for language models, an ontology with SHACL rules, and FAIR metadata. A
deterministic validator checks the scenario a model proposes (values, units, origins, acceptances) before the
unchanged code runs, and the outputs are stored with quantity, unit, origin, provenance and validity limits.

This package provides the Python layer: validation gate, adapters, semantic tools and command-line entry point. The
descriptors, ontology, contracts and the pinned scientific codes (TLS, LQL-Equiv, pyrcel) live in the repository;
full use requires a clone with its submodules.

- Repository and documentation: https://github.com/cyrilvoyant/websemantic
- Ontology (persistent namespace): https://w3id.org/websemantic/ns
- Concept DOI (all versions): https://doi.org/10.5281/zenodo.23238902
- Licence: MIT
