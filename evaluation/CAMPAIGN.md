# Simulation and evaluation campaign — complete register

Updated 7 October 2026, evening. Cases and raw answers are reserved (`benchmark-reserve/`, outside this repository) until the campaign closes; this file lists every series, its design and its status. Only free services are used (Gemini free tier, guest web access, open models on the Serbian HPC).

## Design reminders

- **Interpretation is separated from execution.** A language model returns a scenario JSON; we replay it on the pinned backend (TLS 748e053, LQL-Equiv dfc9a33, pyrcel 977e909) and compare with the reference: nRMSD = RMSD / RMS(reference) on the same grid, relative error on scalar indicators.
- **Corpus**: 60 pilot cases (20 per software, 9 families, 9 scripted continuations) + 18 qualifier cases (« beaucoup de trafic », « peu d'accidents », « dose conventionnelle », « forte ascendance »…). Reserved corpus of 100 cases per software only after the pilot is validated by Cyril.
- **Conditions**: native repository only (F000 = B0) up to the full semantic pack (F111); factorial 2³ over O (ontology + SHACL), C (LLM contract), P (FAIR files).
- **Metrics**: decision accuracy, field accuracy, unsupported values, premature execution, qualifier convention, nRMSD; restatement: verified facts (judge from another model family + 20 % human double reading), wording similarity as secondary; Spearman with objective request complexity; Wilcoxon / McNemar paired by case.

## Register

| # | Series | Design | Calls / runs | Status |
|---|---|---|---|---|
| S0 | Reference calculations | every « execute » case and continuation: TLS (gate-validated scenarios), LQL-Equiv (14 + 2 prescriptions), pyrcel (13 + 3 runs) | ~50 deterministic runs | LQL and pyrcel computed; TLS computed on the fly in `numeric_e1.py`. **To do**: store reference outputs once (CSV + manifest) |
| S1 | E1 documentation ladder B0→B3 | 60 pilot × 4 conditions, Gemini, first turn | 240 (rep 1) | **218/240 done**; reps 2–3 to run with the restatement instruction (never mixed with rep 1) |
| S2 | E1 factorial 2³ (O, C, P) | 78 cases × 8 conditions × 3 reps | 1 872 per model | **Running** with Gemini (rep 1, qualifiers first). To run: open model on the HPC (third family); Mistral free tier if limits allow |
| S3 | Multi-turn continuations | 9 scripted continuations, frozen router + topic lexicon, F000 vs F111 | 9 × 2 × 3 per model | **To do**: multi-turn runner (router and lexicon ready and tested) |
| S4 | E2 dedicated app vs generic model | same 78 cases: WebSemantic CLI (Gemini) vs Gemini F111 | 78 × 2 × 3 | **Blocked**: LQL/pyrcel dedicated runs produced no calculation; CLI restatement output |
| S5 | Online models, guest mode (no account) | 18 qualifier cases × {original repository URL, WebSemantic pack URL} per service | 36 per service | Feasibility: ChatGPT OK (proposes 2.0 for « beaucoup de trafic » vs convention 1.5); Perplexity cannot read GitHub (refuses, invents nothing). **To do**: Copilot test, then full series |
| S6 | Prior familiarity probe | 18 source-free questions (6 categories × 3 software), 65 reference facts | 18 per model / service | **To do** in fresh sessions before S2/S5 interpretation |
| S7 | Restatement validation | judge from another family on all restatements; 20 % human double annotation (kappa) | ~1 900 judgements | **To do** after S2 (judge: open model on the HPC) |
| S8 | Numerical replay | all « execute » answers of S1–S5 replayed, nRMSD / relative errors | deterministic | Script ready (`numeric_e1.py`); pyrcel needs its environment |
| S9 | Reproducibility | replay of manifests in a second environment (Linux HPC) | ~50 runs | **To do** (packaging) |
| S10 | E3 discoverability (exploratory) | online model asked without URL: does it find the original repo / the pack? | ~10 per service | **To do**, descriptive only |
| S11 | Reserved corpus | 100 cases per software, frozen protocol, same series as S2/S5 | ~5 600 per model | **After** validation of the pilot by Cyril |

## Order of execution

1. S2 Gemini rep 1 (running) → score + numeric replay → first factorial results.
2. S5 online series (guest) on the 18 qualifier cases; S6 probe.
3. HPC: open model for S2 (3 reps) and as judge for S7; S9 reproducibility.
4. S3 continuations; S4 once the dedicated app is fixed.
5. S1/S2 reps 2–3 for variability; then S11 on the reserved corpus.
