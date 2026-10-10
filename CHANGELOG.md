# Changelog

Versions follow MAJOR.MINOR.PATCH; each version has a git tag `vX.Y.Z`. Archived versions have a Zenodo DOI under
the concept DOI [10.5281/zenodo.23238902](https://doi.org/10.5281/zenodo.23238902).

## 0.2.6 — 2026-10-10

- Licence MIT from this version on (0.2.0 to 0.2.5 remain under PolyForm Noncommercial 1.0.0).
- Ontology 0.2.6 declares the MIT licence. DOI [10.5281/zenodo.23281295](https://doi.org/10.5281/zenodo.23281295).

## 0.2.5 — 2026-10-10

- Packaging for PyPI (`pip install websemantic`): version, author, URLs, short description; manual Trusted Publishing
  workflow, no stored token.
- SECURITY.md and CONTRIBUTING.md; DOI and PyPI badges in the README.

## 0.2.4 — 2026-10-10

- SHACL checks of returned scenarios: grouped values (objects, lists, dotted and indexed paths) are flattened before
  mapping, without completing any value; unit tests. Upgrade if you reuse `evaluation/e1/validate_answers.py`: the
  previous mapping reported complete groups as incomplete.
- Sensitivity of the contract effect to unparseable answers; spoken-request case archives the Python validation and the
  SHACL checks.
- Ontology 0.2.4: version-independent bibliographic citation.

## 0.2.3 — 2026-10-10

- Ontology IRI `https://w3id.org/websemantic/ns` (hash namespace without `#`). FOOPS! 1.0 on 24 checks.
  DOI [10.5281/zenodo.23276942](https://doi.org/10.5281/zenodo.23276942).

## 0.2.2 — 2026-10-10

- Preferred prefix `wsem` (registered in prefix.cc), ontology logo, data catalogue annotation.

## 0.2.1 — 2026-10-09

- Persistent namespace `https://w3id.org/websemantic/ns#` for the ontology, shapes, contracts and packs.
- Evaluation: preregistered controls (ontology length, generic clarification policy, held-out requests), hallucination
  analysis, full-precision p-values before Holm, ToolRosella baseline scripts, spoken-request case.

## 0.2.0 — 2026-10-08

- First archived release: descriptors, generated contracts, core ontology with SHACL rules and FAIR metadata for three
  unchanged codes at pinned revisions (TLS, LQL-Equiv, pyrcel); validation gate; evaluation harness.
  DOI [10.5281/zenodo.23238903](https://doi.org/10.5281/zenodo.23238903).
