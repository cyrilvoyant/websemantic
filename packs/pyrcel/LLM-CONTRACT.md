# LLM contract — read this file first

Place this pack next to the original code. Files: variables.csv, units.csv, outputs.csv, ontology.ttl, shapes.ttl, codemeta.json.

## Rules

1. **Never invent a value.** Each value is given in the request, an exact conversion of a given value (2 km → 2000 m), a declared default *proposed* to the user, or a declared qualitative convention *proposed* to the user.
2. **Defaults and qualitative conventions need explicit acceptance** before any calculation. « Prends les valeurs par défaut » accepts defaults; it does not accept a qualitative proposal, which needs its own agreement.
3. **Qualitative words have a meaning only through the tables below**, parameter by parameter. A word absent from the tables, or listed under *clarify*, has no numerical meaning: ask.
4. **Units**: use the canonical unit listed. Never mix a percentage and a fraction.
5. **Out of scope → refuse** (see each software).
6. **Conflicts** (two values for one quantity, a total that disagrees with its parts) are reported, never resolved silently.
7. Return the scenario as JSON: `decision` (execute | clarify | refuse), `values` [{field, value, unit, origin, evidence}], `questions`, and a plain three-sentence `restatement` (objective; retained values with units; what still needs acceptance).

Execution is done by the reviewed Python entry points (`agent/README.md`). Never present an unexecuted calculation as a result.

## pyrcel

Original code: https://github.com/darothen/pyrcel (pinned revision in `descriptors/pyrcel/descriptor.yaml`).

Supported: simulate aerosol activation in a constant-updraft parcel with one lognormal mode. Out of scope: weather or cloud forecasts for a real place and time.

| Field | Unit or categories | Bounds | Default (proposal only) | Meaning |
|---|---|---|---|---|
| `V` | unit:M-PER-SEC | min_exclusive 0 | 1 | Vitesse verticale imposée; pas une prévision météorologique. |
| `T0` | unit:K | min_exclusive 0 | 283 | Température absolue initiale de la parcelle. |
| `P0` | unit:PA | min_exclusive 0 | 85000 | Pression absolue initiale. |
| `S0` | unit:UNITLESS | min_exclusive -1, max 0 | -0.02 | S0 = humidité relative en fraction - 1; -0,02 correspond à 98 %. |
| `N` | unit:PER-CentiM3 | min_exclusive 0 | 1000 | Nombre initial de particules de la distribution lognormale par cm³. |
| `mu` | unit:MicroM | min_exclusive 0 | 0.05 | Rayon sec médian géométrique; pas le diamètre. |
| `sigma` | unit:UNITLESS | min_exclusive 1 | 2 | Écart type géométrique de la distribution lognormale. |
| `kappa` | unit:UNITLESS | min 0 | 0.54 | Paramètre κ de Köhler. |
| `bins` | unit:NUM | min 2, max 200 | 50 | Discrétisation de la distribution; borne haute du profil local. |
| `accom` | unit:UNITLESS | min_exclusive 0, max 1 | 1 | Coefficient d’accommodation de vapeur. |
| `t_end` | unit:SEC | min_exclusive 0, max 3000 | 3000 | Limite de temps; la terminaison peut survenir avant. |
| `output_dt` | unit:SEC | min_exclusive 0 | 1 | Le dernier instant peut être irrégulier. |
| `terminate` | unit:UNITLESS |  | yes | yes: arrêt après maximum; no: intégration jusqu’à t_end. |
| `terminate_depth` | unit:M | min_exclusive 0 | 10 | Distance ascendante après le maximum de sursaturation. |

**Qualitative conventions** (propose the value, then ask for acceptance):

None declared.

**Clarify, never convert:** « faible / forte ascendance », « air pur / marin / pollué / continental », « air presque saturé ».
