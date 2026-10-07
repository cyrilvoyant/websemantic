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

## Tunnel Load Simulator (TLS)

Original code: https://github.com/cyrilvoyant/tunnel-load-simulator (pinned revision in `descriptors/tls/descriptor.yaml`).

Supported: estimate electricity demand (energy, peak, load factor) of a road tunnel under stated assumptions; compare configurations (lighting, ventilation, traffic) with controlled seeds; characterise stochastic variability from modelled events. Out of scope: certification or prediction of a real tunnel's consumption.

| Field | Unit or categories | Bounds | Default (proposal only) | Meaning |
|---|---|---|---|---|
| `length_m` | unit:M | min_exclusive 0 | 1500 | Longueur du tunnel commune aux tubes ; convertie en kilomètres pour les charges proportionnelles à la longueur. |
| `n_tubes` | unit:NUM | min 1, max 8 | 2 | Nombre de tubes ; multiplie les charges de ventilation et d’auxiliaires et contribue au nombre total de voies. |
| `n_lanes_per_tube` | unit:NUM | min 1, max 6 | 2 | Nombre de voies dans chaque tube ; l’éclairage est dimensionné sur n_tubes × n_lanes_per_tube. |
| `altitude_m` | unit:M |  | 300 | Altitude utilisée dans le facteur de ventilation : 1 + max(altitude_m − 500, 0)/6000. |
| `max_depth_m` | unit:M |  | 80 | Profondeur maximale utilisée pour les auxiliaires : facteur 1 + min(max_depth_m, 800)/6000. |
| `gradient_percent` | unit:PERCENT |  | 2.0 | Pente en pourcentage, utilisée dans le facteur de ventilation 1 + abs(gradient_percent)/20. |
| `tunnel_context` | categories: urban, peri-urban, rural |  | peri-urban | Catégorie appliquant un multiplicateur au profil de trafic ; urban ajoute également une composante de pointe en soirée. |
| `lighting_type` | categories: LED adaptive, LED fixed, mixed, sodium fixed |  | LED adaptive | Catégorie déterminant la puissance spécifique installée, le couplage au trafic et la fraction minimale d’éclairage. |
| `ventilation_type` | categories: natural/low ventilation, longitudinal, semi-transverse, transverse |  | longitudinal | Catégorie déterminant la charge de ventilation par kilomètre et par tube, modulée par trafic, altitude, pente et événements. |
| `aux_kw_per_km_tube` | unit:KiloW per km per tube |  | 35.0 | Charge de référence des auxiliaires en kW/(km·tube), multipliée par la longueur, les tubes et le facteur de profondeur. |
| `base_fixed_kw` | unit:KiloW |  | 40.0 | Puissance fixe ajoutée une seule fois à la demande totale du tunnel, avant le bruit multiplicatif global. |
| `traffic_level` | unit:UNITLESS |  | 1.0 | Multiplicateur du profil synthétique de trafic normalisé ; l’indice final est borné entre 0 et 2 dans TLS. |
| `morning_peak_hour` | unit:HR |  | 8.0 | Heure du centre du pic gaussien du matin, comprise entre 0 inclus et 24 exclu. |
| `evening_peak_hour` | unit:HR |  | 18.0 | Heure du centre du pic gaussien du soir, comprise entre 0 inclus et 24 exclu. |
| `peak_width_h` | unit:HR |  | 1.4 | Écart-type temporel du pic gaussien du matin en heures ; TLS utilise 1,15 fois cette valeur pour le soir. |
| `traffic_sensitivity` | unit:UNITLESS |  | 0.65 | Coefficient du trafic dans la charge de ventilation : facteur 0,15 + traffic_sensitivity × traffic_index. |
| `noise_sigma` | unit:UNITLESS | min 0 | 0.06 | Écart-type du bruit gaussien relatif appliqué à la puissance totale ; la puissance résultante est ramenée au minimum à zéro. |
| `pollution_probability_per_day` | unit:UNITLESS | min 0, max 1 | 0.05 | Probabilité journalière de tirer un événement synthétique de pollution ; TLS tire ensuite son début et sa durée. |
| `accident_probability_per_day` | unit:UNITLESS | min 0, max 1 | 0.015 | Probabilité journalière de tirer un événement synthétique d’accident ; TLS tire ensuite son début et sa durée. |
| `pollution_sensitivity` | unit:UNITLESS |  | 0.55 | Coefficient de surcroît de ventilation lorsqu’un événement de pollution est actif : ajout à 1 + pollution_sensitivity × indicateur. |
| `accident_sensitivity` | unit:UNITLESS |  | 0.75 | Coefficient de surcroît de ventilation lorsqu’un accident est actif ; il s’ajoute au coefficient de pollution dans le même facteur. |
| `start_date` |  |  | 2025-01-01 | Date de début au format YYYY-MM-DD ; détermine le calendrier, les jours de semaine et les saisons du modèle. |
| `n_days` | unit:DAY | min 1 | 7 | Nombre de jours entiers simulés à partir de start_date. |
| `freq_minutes` | unit:MIN | min 1 | 60 | Durée constante du pas interne ; l’énergie du pas vaut puissance × freq_minutes/60. |
| `n_runs` | unit:NUM | min 1 | 3 | Nombre de réalisations Monte Carlo indépendantes ; chaque réalisation utilise base_seed + son indice. |
| `base_seed` |  | min 0 | 42 | Identifiant initial du générateur pseudo-aléatoire ; chaque réalisation utilise base_seed + run. |

**Qualitative conventions** (propose the value, then ask for acceptance):

| Expression | Field | Proposed value |
|---|---|---|
| « tunnel court », « faible longueur » | `length_m` | 375.0 unit:M |
| « longueur courante » | `length_m` | 1500 unit:M |
| « tunnel long », « grande longueur » | `length_m` | 9000.0 unit:M |
| « tunnel très long », « très grande longueur » | `length_m` | 12000.0 unit:M |
| « peu de tubes » | `n_tubes` | 1 unit:NUM |
| « nombre courant de tubes » | `n_tubes` | 2 unit:NUM |
| « beaucoup de tubes » | `n_tubes` | 3 unit:NUM |
| « énormément de tubes » | `n_tubes` | 4 unit:NUM |
| « peu de voies par tube » | `n_lanes_per_tube` | 1 unit:NUM |
| « nombre courant de voies par tube » | `n_lanes_per_tube` | 2 unit:NUM |
| « beaucoup de voies par tube » | `n_lanes_per_tube` | 3 unit:NUM |
| « énormément de voies par tube » | `n_lanes_per_tube` | 4 unit:NUM |
| « faible altitude », « basse altitude » | `altitude_m` | 75.0 unit:M |
| « altitude courante » | `altitude_m` | 300 unit:M |
| « haute altitude », « altitude élevée » | `altitude_m` | 2250.0 unit:M |
| « très haute altitude », « altitude très élevée » | `altitude_m` | 3000.0 unit:M |
| « faible profondeur », « tunnel peu profond » | `max_depth_m` | 20.0 unit:M |
| « profondeur courante » | `max_depth_m` | 80 unit:M |
| « grande profondeur », « tunnel profond » | `max_depth_m` | 750.0 unit:M |
| « très grande profondeur », « tunnel très profond » | `max_depth_m` | 1000.0 unit:M |
| « faible pente », « pente faible » | `gradient_percent` | 0.5 unit:PERCENT |
| « pente courante » | `gradient_percent` | 2.0 unit:PERCENT |
| « forte pente », « pente forte » | `gradient_percent` | 9.0 unit:PERCENT |
| « très forte pente », « pente très forte » | `gradient_percent` | 12.0 unit:PERCENT |
| « faible charge auxiliaire », « auxiliaires peu puissants » | `aux_kw_per_km_tube` | 8.75 unit:KiloW per km per tube |
| « charge auxiliaire courante » | `aux_kw_per_km_tube` | 35.0 unit:KiloW per km per tube |
| « forte charge auxiliaire », « auxiliaires puissants » | `aux_kw_per_km_tube` | 90.0 unit:KiloW per km per tube |
| « très forte charge auxiliaire », « auxiliaires très puissants » | `aux_kw_per_km_tube` | 120.0 unit:KiloW per km per tube |
| « faible charge fixe », « charge fixe faible » | `base_fixed_kw` | 10.0 unit:KiloW |
| « charge fixe courante » | `base_fixed_kw` | 40.0 unit:KiloW |
| « forte charge fixe », « charge fixe élevée » | `base_fixed_kw` | 375.0 unit:KiloW |
| « très forte charge fixe », « charge fixe très élevée » | `base_fixed_kw` | 500.0 unit:KiloW |
| « beaucoup de trafic », « beaucoup de traffic », « trafic important », « trafic élevé », « fort trafic » | `traffic_level` | 1.5 unit:UNITLESS |
| « énormément de trafic », « énormément de traffic », « trafic très élevé », « trafic énorme » | `traffic_level` | 2.0 unit:UNITLESS |
| « peu de trafic », « faible trafic », « trafic faible » | `traffic_level` | 0.3 unit:UNITLESS |
| « trafic courant » | `traffic_level` | 1.0 unit:UNITLESS |
| « pointe du matin tôt », « pic du matin précoce » | `morning_peak_hour` | 5 unit:HR |
| « pointe du matin courante » | `morning_peak_hour` | 8 unit:HR |
| « pointe du matin tardive », « pic du matin tardif » | `morning_peak_hour` | 11 unit:HR |
| « pointe du soir tôt », « pic du soir précoce » | `evening_peak_hour` | 15 unit:HR |
| « pointe du soir courante » | `evening_peak_hour` | 18 unit:HR |
| « pointe du soir tardive », « pic du soir tardif » | `evening_peak_hour` | 22 unit:HR |
| « pics de trafic étroits », « pointes étroites » | `peak_width_h` | 0.35 unit:HR |
| « largeur de pointe courante » | `peak_width_h` | 1.4 unit:HR |
| « pics de trafic larges », « pointes larges » | `peak_width_h` | 3.0 unit:HR |
| « pics de trafic très larges », « pointes très larges » | `peak_width_h` | 4.0 unit:HR |
| « faible sensibilité au trafic » | `traffic_sensitivity` | 0.1625 unit:UNITLESS |
| « sensibilité au trafic courante » | `traffic_sensitivity` | 0.65 unit:UNITLESS |
| « forte sensibilité au trafic » | `traffic_sensitivity` | 1.125 unit:UNITLESS |
| « très forte sensibilité au trafic » | `traffic_sensitivity` | 1.5 unit:UNITLESS |
| « faible bruit relatif », « faible bruit gaussien » | `noise_sigma` | 0.015 unit:UNITLESS |
| « bruit relatif courant » | `noise_sigma` | 0.06 unit:UNITLESS |
| « fort bruit relatif », « bruit gaussien élevé » | `noise_sigma` | 0.375 unit:UNITLESS |
| « très fort bruit relatif », « bruit gaussien très élevé » | `noise_sigma` | 0.5 unit:UNITLESS |
| « faible probabilité de pollution », « événements de pollution rares » | `pollution_probability_per_day` | 0.0125 unit:UNITLESS |
| « probabilité de pollution courante » | `pollution_probability_per_day` | 0.05 unit:UNITLESS |
| « forte probabilité de pollution », « événements de pollution fréquents » | `pollution_probability_per_day` | 0.375 unit:UNITLESS |
| « très forte probabilité de pollution », « événements de pollution très fréquents » | `pollution_probability_per_day` | 0.5 unit:UNITLESS |
| « faible probabilité d’accident », « accidents rares » | `accident_probability_per_day` | 0.00375 unit:UNITLESS |
| « probabilité d’accident courante » | `accident_probability_per_day` | 0.015 unit:UNITLESS |
| « forte probabilité d’accident », « accidents fréquents » | `accident_probability_per_day` | 0.15 unit:UNITLESS |
| « très forte probabilité d’accident », « accidents très fréquents » | `accident_probability_per_day` | 0.2 unit:UNITLESS |
| « faible sensibilité à la pollution » | `pollution_sensitivity` | 0.1375 unit:UNITLESS |
| « sensibilité à la pollution courante » | `pollution_sensitivity` | 0.55 unit:UNITLESS |
| « forte sensibilité à la pollution » | `pollution_sensitivity` | 1.5 unit:UNITLESS |
| « très forte sensibilité à la pollution » | `pollution_sensitivity` | 2.0 unit:UNITLESS |
| « faible sensibilité aux accidents » | `accident_sensitivity` | 0.1875 unit:UNITLESS |
| « sensibilité aux accidents courante » | `accident_sensitivity` | 0.75 unit:UNITLESS |
| « forte sensibilité aux accidents » | `accident_sensitivity` | 1.5 unit:UNITLESS |
| « très forte sensibilité aux accidents » | `accident_sensitivity` | 2.0 unit:UNITLESS |
| « courte période de simulation », « simulation courte » | `n_days` | 1 unit:DAY |
| « durée de simulation courante » | `n_days` | 7 unit:DAY |
| « longue période de simulation », « simulation longue » | `n_days` | 365 unit:DAY |
| « très longue période de simulation », « simulation très longue » | `n_days` | 1095 unit:DAY |
| « pas très fin », « résolution temporelle très fine » | `freq_minutes` | 5 unit:MIN |
| « pas fin », « résolution temporelle fine » | `freq_minutes` | 10 unit:MIN |
| « pas intermédiaire » | `freq_minutes` | 15 unit:MIN |
| « pas large » | `freq_minutes` | 30 unit:MIN |
| « pas grossier », « résolution temporelle grossière » | `freq_minutes` | 60 unit:MIN |
| « peu de réalisations » | `n_runs` | 1 unit:NUM |
| « nombre courant de réalisations » | `n_runs` | 3 unit:NUM |
| « beaucoup de réalisations » | `n_runs` | 30 unit:NUM |
| « énormément de réalisations » | `n_runs` | 50 unit:NUM |

**Clarify, never convert:** « fortement / faiblement éclairé » (TLS has no illuminance parameter); « ancien éclairage » (no category).
