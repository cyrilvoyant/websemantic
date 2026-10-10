---
title: WebSemantic
emoji: 📐
colorFrom: gray
colorTo: gray
sdk: static
app_file: index.html
pinned: true
license: mit
short_description: Scientific codes that ask before they compute
tags:
  - scientific-software
  - semantic-web
  - ontology
  - radiotherapy
  - energy
  - pyodide
---

# WebSemantic — ask before you compute

Talk to two scientific codes, in English or French, by text or voice: **road-tunnel electricity demand** (Tunnel
Load Simulator) and **radiotherapy dose equivalence** (LQL-Equiv). The code asks for what is missing, proposes its
declared conventions for vague words ("a lot of traffic", "a long tunnel"), and computes only what you accepted.
Results come with units, time series, a short analysis and their provenance (code revision, DOI, validity limits).

The pinned codes run **in your browser** (Pyodide), after their sources are checked by SHA-256. A language model
(Mistral) only reads each message against the code's contract, through a small relay that keeps the key secret.
Scenarios are fictitious by design: do not enter personal or patient data.

- Source: https://github.com/cyrilvoyant/websemantic (MIT) · PyPI: `pip install websemantic`
- Concept DOI: https://doi.org/10.5281/zenodo.23238902 · Ontology: https://w3id.org/websemantic/ns
- Author: Cyril Voyant, Mines Paris – PSL ([ORCID 0000-0003-0242-7377](https://orcid.org/0000-0003-0242-7377))
