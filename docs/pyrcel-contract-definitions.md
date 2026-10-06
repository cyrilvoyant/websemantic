# pyrcel contract: concept definitions (draft for review)

pyrcel 2.0.0, BSD-3-Clause, revision `977e9094644ec4a17d658d657094651928591c89`, used unmodified. API read on 6 October 2026: `AerosolSpecies`, `Lognorm`, `ParcelModel`, `ParcelModel.run`, `ModelOutput`. Adapter and descriptor YAML are implemented separately and must match this revision. Scientific conventions to be reviewed before activation.

## 1. Task profiles

| Profile | Status |
|---|---|
| Simulate the adiabatic ascent of an air parcel and the activation of a stated aerosol population at a stated updraft and initial state | supported |
| Compare two aerosol populations or updrafts with identical numerical settings | supported |
| Forecast clouds or precipitation for a real place and time | **excluded**: refuse |
| Time-varying updraft `V(t)`, ensemble runs, GPU settings | out of the first profile: clarify |

## 2. Inputs

| Field | API | Meaning | Unit | Bounds (authority) | Default (origin) |
|---|---|---|---|---|---|
| `V` | `ParcelModel(V=…)` | Constant updraft speed | m/s | > 0 (profile policy) | none: must be stated |
| `T0` | `ParcelModel(T0=…)` | Initial temperature | K (°C converted exactly) | > 0 (physics) | none |
| `P0` | `ParcelModel(P0=…)` | Initial pressure | Pa (hPa converted exactly) | > 0 (physics) | none |
| `S0` | `ParcelModel(S0=…)` | Initial supersaturation; 0 = 100 % RH, −0.02 = 98 % RH | 1 | −1 < S0 ≤ 0 (profile policy: sub-saturated start, RH > 0) | none; RH in % → S0 = RH/100 − 1 (98 % → −0.02); RH as a fraction → S0 = RH − 1 |
| `aerosols[k].species` | `AerosolSpecies(species)` | Label of mode k | text | — | none |
| `aerosols[k].N` | `Lognorm(N=…)` | Total number concentration of mode k | cm⁻³ | > 0 (profile) | none |
| `aerosols[k].mu` | `Lognorm(mu=…)` | Median (geometric mean) dry radius | μm | > 0 (profile) | none |
| `aerosols[k].sigma` | `Lognorm(sigma=…)` | Geometric standard deviation | 1 | > 1 (profile) | none |
| `aerosols[k].kappa` | `AerosolSpecies(kappa=…)` | Hygroscopicity parameter κ | 1 | ≥ 0 (profile) | none |
| `aerosols[k].bins` | `AerosolSpecies(bins=…)` | Number of size bins | count | ≥ 1 (code) | protocol default, frozen before the campaign and logged; affects results, never changed silently |
| `accom` | `ParcelModel(accom=…)` | Condensation coefficient | 1 | (0, 1] | 1.0 (code constant `ac`, stated in answers) |
| `t_end` | `run(t_end=…)` | Maximum integration time | s | > 0 | protocol default, frozen and logged |
| `output_dt` | `run(output_dt=…)` | Output cadence | s | > 0 | protocol default, frozen and logged |
| `terminate`, `terminate_depth` | `run(...)` | Stop `terminate_depth` m above S_max | boolean, m | — | protocol default, frozen and logged; changes the trajectory length |

Numerical settings (`bins`, `t_end`, `output_dt`, termination) change results: their protocol values are fixed before the campaign, recorded in every manifest, and identical across compared runs.

Units are a contract point: pyrcel interprets `mu` in μm and `N` in cm⁻³ for parcel runs, while the activated droplet number `Nd` is returned in m⁻³. Any answer must state the unit used.

Relational rules (condition B3):
- relative humidity and `S0` are one quantity (`S0 = RH − 1`): both given and inconsistent means a conflict;
- °C and K, hPa and Pa are exact conversions, not inferences;
- one aerosol mode needs all four of `N`, `mu`, `sigma`, `kappa`: a partial mode means clarify.

## 3. Outputs

| Output | API | Unit | Support | Notes |
|---|---|---|---|---|
| Height `z` | `to_pandas()` parcel table | m | output grid | Above the starting level, not altitude above sea level |
| Pressure `P`, temperature `T` | parcel table | Pa, K | output grid | |
| Water vapour, liquid, ice `wv`, `wc`, `wi` | parcel table | kg/kg | output grid | Mixing ratios |
| Supersaturation `S` | parcel table | 1 | output grid | Report as % only if stated (`S × 100`) |
| `S_max` | `summary["S_max"]` | 1 | whole run | Maximum supersaturation from pyrcel's peak locator; may differ from the maximum of the sampled `S` column. Kept as a native KPI; the CSV maximum is not presented as S_max |
| `Nd` | `ModelOutput.Nd` | m⁻³ | at end of run | Activated droplets; convert to cm⁻³ only explicitly |
| Activated fraction | `ModelOutput.nd_frac` | 1 | at end of run | |

Numerical comparisons: RMSD on one quantity at a time, on the same output grid (same `output_dt`, same termination rule); absolute and relative error on `S_max`, `Nd` and activated fraction.

## 4. Qualifiers

| Expression | Field | Treatment |
|---|---|---|
| « faible / modérée / forte ascendance » | `V` | **Clarification**: the user states V; no numerical convention before sourced review |
| « air pur », « marin », « pollué », « continental » | aerosol `N` (and mode) | **Clarification**: no aerosol population is proposed without a cited source |
| « sulfate d'ammonium », « sel marin » | `kappa` | Proposal only with a cited κ value, to accept |
| « air presque saturé », « humidité 98 % » | `S0` | Numerical RH: exact conversion; « presque saturé » alone: clarification |
| « plus de particules » | `N` | **Clarification**: no factor or new value is given |
| « deux fois plus d'aérosols » | `N` | Explicit factor on an existing value: N × 2, the interpretation stated and accepted before the run |

## 5. Refusal policy

Refuse a forecast for a real place and time (« va-t-il pleuvoir à Lyon demain ? »). A parcel run with stated conditions is in scope, including conditions described as typical of a place, provided all values are supplied or accepted.

## 6. Competency questions added

| # | Question | Expected answer | Mechanism |
|---|---|---|---|
| CQ12 | Which inputs define a run, in which units? | V (m/s), T0 (K), P0 (Pa), S0 (1), aerosol modes (N cm⁻³, μ μm, σ, κ) | graph |
| CQ17 | Are relative humidity and S0 independent? | No: S0 = RH − 1 | graph rule (B3) |
| CQ18 | In which unit is `Nd` returned? | m⁻³, not cm⁻³ | graph |
| CQ19 | Does « air pollué » fix an aerosol population? | No: clarification | graph |
| CQ20 | Is a rain forecast for a city in scope? | No: refuse | rules |
