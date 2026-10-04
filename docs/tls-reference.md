# Paramètres et sorties TLS

Référence du modèle TLS à la révision indiquée dans le contrat. Les définitions et les colonnes sont maintenues à partir du descripteur et des métadonnées de calcul.

Les défauts scientifiques sont des propositions non calibrées, à accepter explicitement. Tous les paramètres sont requis dans la configuration ; les réglages operational_default sont fournis automatiquement selon la politique utilisateur.

## inputs

| Champ | Définition | Type | Unité canonique / lisible | Défaut proposé | Contraintes déclarées |
|---|---|---|---|---|---|
| `length_m` | Longueur du tunnel commune aux tubes ; convertie en kilomètres pour les charges proportionnelles à la longueur. | float | `unit:M` / m | 1500 | {"bounds": {"min_exclusive": 0, "authority": "code"}} |
| `n_tubes` | Nombre de tubes ; multiplie les charges de ventilation et d’auxiliaires et contribue au nombre total de voies. | int | `unit:NUM` / nombre | 2 | {"bounds": {"min": 1, "max": 8, "authority": "code"}} |
| `n_lanes_per_tube` | Nombre de voies dans chaque tube ; l’éclairage est dimensionné sur n_tubes × n_lanes_per_tube. | int | `unit:NUM` / nombre | 2 | {"bounds": {"min": 1, "max": 6, "authority": "code"}} |
| `altitude_m` | Altitude utilisée dans le facteur de ventilation : 1 + max(altitude_m − 500, 0)/6000. | float | `unit:M` / m | 300 | {} |
| `max_depth_m` | Profondeur maximale utilisée pour les auxiliaires : facteur 1 + min(max_depth_m, 800)/6000. | float | `unit:M` / m | 80 | {} |
| `gradient_percent` | Pente en pourcentage, utilisée dans le facteur de ventilation 1 + abs(gradient_percent)/20. | float | `unit:PERCENT` / % | 2.0 | {} |
| `tunnel_context` | Catégorie appliquant un multiplicateur au profil de trafic ; urban ajoute également une composante de pointe en soirée. | category | `None` / catégorie | peri-urban | {"values": ["urban", "peri-urban", "rural"]} |
| `lighting_type` | Catégorie déterminant la puissance spécifique installée, le couplage au trafic et la fraction minimale d’éclairage. | category | `None` / catégorie | LED adaptive | {"values": ["LED adaptive", "LED fixed", "mixed", "sodium fixed"]} |
| `ventilation_type` | Catégorie déterminant la charge de ventilation par kilomètre et par tube, modulée par trafic, altitude, pente et événements. | category | `None` / catégorie | longitudinal | {"values": ["natural/low ventilation", "longitudinal", "semi-transverse", "transverse"]} |
| `aux_kw_per_km_tube` | Charge de référence des auxiliaires en kW/(km·tube), multipliée par la longueur, les tubes et le facteur de profondeur. | float | `unit:KiloW per km per tube` / kW/(km·tube) | 35.0 | {} |
| `base_fixed_kw` | Puissance fixe ajoutée une seule fois à la demande totale du tunnel, avant le bruit multiplicatif global. | float | `unit:KiloW` / kW | 40.0 | {} |
| `traffic_level` | Multiplicateur du profil synthétique de trafic normalisé ; l’indice final est borné entre 0 et 2 dans TLS. | float | `unit:UNITLESS` / 1 | 1.0 | {} |
| `morning_peak_hour` | Heure du centre du pic gaussien du matin, comprise entre 0 inclus et 24 exclu. | float | `unit:HR` / h du jour | 8.0 | {} |
| `evening_peak_hour` | Heure du centre du pic gaussien du soir, comprise entre 0 inclus et 24 exclu. | float | `unit:HR` / h du jour | 18.0 | {} |
| `peak_width_h` | Écart-type temporel du pic gaussien du matin en heures ; TLS utilise 1,15 fois cette valeur pour le soir. | float | `unit:HR` / h | 1.4 | {} |
| `traffic_sensitivity` | Coefficient du trafic dans la charge de ventilation : facteur 0,15 + traffic_sensitivity × traffic_index. | float | `unit:UNITLESS` / 1 | 0.65 | {} |
| `noise_sigma` | Écart-type du bruit gaussien relatif appliqué à la puissance totale ; la puissance résultante est ramenée au minimum à zéro. | float | `unit:UNITLESS` / 1 | 0.06 | {"bounds": {"min": 0, "authority": "code"}} |
| `pollution_probability_per_day` | Probabilité journalière de tirer un événement synthétique de pollution ; TLS tire ensuite son début et sa durée. | float | `unit:UNITLESS` / 1 | 0.05 | {"bounds": {"min": 0, "max": 1, "authority": "code"}} |
| `accident_probability_per_day` | Probabilité journalière de tirer un événement synthétique d’accident ; TLS tire ensuite son début et sa durée. | float | `unit:UNITLESS` / 1 | 0.015 | {"bounds": {"min": 0, "max": 1, "authority": "code"}} |
| `pollution_sensitivity` | Coefficient de surcroît de ventilation lorsqu’un événement de pollution est actif : ajout à 1 + pollution_sensitivity × indicateur. | float | `unit:UNITLESS` / 1 | 0.55 | {} |
| `accident_sensitivity` | Coefficient de surcroît de ventilation lorsqu’un accident est actif ; il s’ajoute au coefficient de pollution dans le même facteur. | float | `unit:UNITLESS` / 1 | 0.75 | {} |

## experiment

| Champ | Définition | Type | Unité canonique / lisible | Défaut proposé | Contraintes déclarées |
|---|---|---|---|---|---|
| `start_date` | Date de début au format YYYY-MM-DD ; détermine le calendrier, les jours de semaine et les saisons du modèle. | date | `None` / date | 2025-01-01 | {} |
| `n_days` | Nombre de jours entiers simulés à partir de start_date. | int | `unit:DAY` / jours | 7 | {"bounds": {"min": 1, "authority": "policy"}} |
| `freq_minutes` | Durée constante du pas interne ; l’énergie du pas vaut puissance × freq_minutes/60. | int | `unit:MIN` / min | 60 | {"bounds": {"min": 1, "authority": "policy"}} |
| `n_runs` | Nombre de réalisations Monte Carlo indépendantes ; chaque réalisation utilise base_seed + son indice. | int | `unit:NUM` / nombre | 3 | {"bounds": {"min": 1, "authority": "policy"}} |
| `base_seed` | Identifiant initial du générateur pseudo-aléatoire ; chaque réalisation utilise base_seed + run. | int | `None` / identifiant | 42 | {"bounds": {"min": 0, "authority": "policy"}} |

## Rôle et précautions d'interprétation

- `inputs.length_m` — geometry ; length. Ne pas multiplier la longueur par le nombre de tubes ; ce facteur est appliqué séparément.
- `inputs.n_tubes` — geometry ; count. Un tube est distinct d’une voie de circulation.
- `inputs.n_lanes_per_tube` — geometry ; count. Ne pas fournir le nombre total de voies à la place du nombre par tube.
- `inputs.altitude_m` — ventilation ; length. Le référentiel altimétrique n’est pas déclaré par le modèle ; l’altitude de la commune ne fixe pas celle du tunnel.
- `inputs.max_depth_m` — auxiliaries ; length. Le plafonnement de l’effet à 800 m n’est pas une limite géométrique de validité physique.
- `inputs.gradient_percent` — ventilation ; percentage. Une pente de 2 % se saisit 2, pas 0,02 ; l’adaptateur courant demande une valeur non négative.
- `inputs.tunnel_context` — traffic ; category. Le contexte n’est pas une commune et ne constitue pas une calibration du trafic.
- `inputs.lighting_type` — lighting ; category. Même les catégories fixed ont une modulation horaire dans ce modèle ; aucun éclairement en lux n’est calculé.
- `inputs.ventilation_type` — ventilation ; category. Il s’agit d’une charge électrique synthétique, pas d’un débit d’air ni d’une vérification de sécurité.
- `inputs.aux_kw_per_km_tube` — auxiliaries ; linear_power_per_tube. Ne pas confondre cette charge linéique avec une énergie ; un bruit propre aux auxiliaires est ajouté par TLS.
- `inputs.base_fixed_kw` — base_load ; power. Cette puissance concerne l’ensemble du tunnel, pas chaque tube.
- `inputs.traffic_level` — traffic ; dimensionless_multiplier. Ce paramètre n’est ni un débit en véhicules/heure ni un trafic journalier observé.
- `inputs.morning_peak_hour` — traffic ; time_of_day. Heure du calendrier simulé ; aucun fuseau horaire ni changement d’heure n’est modélisé.
- `inputs.evening_peak_hour` — traffic ; time_of_day. Heure du calendrier simulé ; aucun fuseau horaire ni changement d’heure n’est modélisé.
- `inputs.peak_width_h` — traffic ; duration. Ce n’est pas la durée totale de la pointe ni sa largeur à mi-hauteur.
- `inputs.traffic_sensitivity` — ventilation ; dimensionless_coefficient. Coefficient de modèle ; ce n’est pas une élasticité mesurée de consommation.
- `inputs.noise_sigma` — stochastic ; relative_standard_deviation. D’autres tirages restent actifs même si noise_sigma=0 : trafic quotidien, auxiliaires et événements.
- `inputs.pollution_probability_per_day` — stochastic ; daily_event_probability. Une valeur de 0,05 signifie une probabilité de 5 % par jour, pas un taux de pollution ni une concentration.
- `inputs.accident_probability_per_day` — stochastic ; daily_event_probability. Ce n’est pas une fréquence d’accident par véhicule ni une statistique directement déduite de BAAC.
- `inputs.pollution_sensitivity` — ventilation ; dimensionless_coefficient. Quand les deux événements sont actifs, leurs coefficients s’ajoutent ; aucune dispersion atmosphérique n’est simulée.
- `inputs.accident_sensitivity` — ventilation ; dimensionless_coefficient. Ce paramètre ne représente ni la gravité ni le coût énergétique complet d’un accident réel.
- `experiment.start_date` — experiment ; calendar_date. Pas de fuseau déclaré ; le profil de lumière saisonnier est celui du modèle, pas une éphéméride du site.
- `experiment.n_days` — experiment ; duration_days. L’annualisation utilise 365/n_days ; 365 jours ne couvrent pas une année civile bissextile complète.
- `experiment.freq_minutes` — experiment ; duration_minutes. Pas admis : 5, 10, 15, 30 ou 60 min. Une sortie quotidienne est une agrégation, pas un calcul à minuit.
- `experiment.n_runs` — experiment ; count. Augmenter ce nombre décrit mieux la variabilité du modèle, sans ajouter une validation terrain.
- `experiment.base_seed` — operational ; identifier. Valeur fixe 42 selon la politique d’essai, modifiable explicitement ; ce n’est pas un paramètre physique.
### Convention qualitative — `inputs.length_m`

Valeur de scénario proposée, à valider. Le niveau courant reprend le défaut déclaré ; élevé et très élevé utilisent 75 % et 100 % de la référence haute du curseur. Ces niveaux ne sont pas des statistiques observées.

| Expression | Règle | Valeur | Unité ou type |
|---|---|---|---|
| faible | Valeur déclarée | 375.0 | m |
| courant | Valeur déclarée | 1500 | m |
| élevé | 0.75 × 12000.0 | 9000.0 | m |
| très élevé | 1.0 × 12000.0 | 12000.0 | m |

Convention d’essai WebSemantic ; références de curseurs vérifiées dans TLS app.py @748e053e129669cf3e896d381e3c0ac01c763edd. Ni limite physique ni calibration terrain.

La valeur numérique explicite reste prioritaire. Les qualificatifs non déclarés demandent une clarification.

### Convention qualitative — `inputs.n_tubes`

Comptages entiers de scénario, à valider ; références discrètes de l’interface TLS, pas maxima du moteur.

| Expression | Règle | Valeur | Unité ou type |
|---|---|---|---|
| peu | Valeur déclarée | 1 | nombre |
| courant | Valeur déclarée | 2 | nombre |
| beaucoup | Valeur déclarée | 3 | nombre |
| maximum de référence | Valeur déclarée | 4 | nombre |

Convention d’essai WebSemantic ; références de curseurs vérifiées dans TLS app.py @748e053e129669cf3e896d381e3c0ac01c763edd. Ni limite physique ni calibration terrain.

La valeur numérique explicite reste prioritaire. Les qualificatifs non déclarés demandent une clarification.

### Convention qualitative — `inputs.n_lanes_per_tube`

Comptage par tube, à valider ; ne pas le confondre avec le total de voies.

| Expression | Règle | Valeur | Unité ou type |
|---|---|---|---|
| peu | Valeur déclarée | 1 | nombre |
| courant | Valeur déclarée | 2 | nombre |
| beaucoup | Valeur déclarée | 3 | nombre |
| maximum de référence | Valeur déclarée | 4 | nombre |

Convention d’essai WebSemantic ; références de curseurs vérifiées dans TLS app.py @748e053e129669cf3e896d381e3c0ac01c763edd. Ni limite physique ni calibration terrain.

La valeur numérique explicite reste prioritaire. Les qualificatifs non déclarés demandent une clarification.

### Convention qualitative — `inputs.altitude_m`

Valeur de scénario proposée, à valider. Le niveau courant reprend le défaut déclaré ; élevé et très élevé utilisent 75 % et 100 % de la référence haute du curseur. Ces niveaux ne sont pas des statistiques observées.

| Expression | Règle | Valeur | Unité ou type |
|---|---|---|---|
| faible | Valeur déclarée | 75.0 | m |
| courant | Valeur déclarée | 300 | m |
| élevé | 0.75 × 3000.0 | 2250.0 | m |
| très élevé | 1.0 × 3000.0 | 3000.0 | m |

Convention d’essai WebSemantic ; références de curseurs vérifiées dans TLS app.py @748e053e129669cf3e896d381e3c0ac01c763edd. Ni limite physique ni calibration terrain.

La valeur numérique explicite reste prioritaire. Les qualificatifs non déclarés demandent une clarification.

### Convention qualitative — `inputs.max_depth_m`

Valeur de scénario proposée, à valider. Le niveau courant reprend le défaut déclaré ; élevé et très élevé utilisent 75 % et 100 % de la référence haute du curseur. Ces niveaux ne sont pas des statistiques observées.

| Expression | Règle | Valeur | Unité ou type |
|---|---|---|---|
| faible | Valeur déclarée | 20.0 | m |
| courant | Valeur déclarée | 80 | m |
| élevé | 0.75 × 1000.0 | 750.0 | m |
| très élevé | 1.0 × 1000.0 | 1000.0 | m |

Convention d’essai WebSemantic ; références de curseurs vérifiées dans TLS app.py @748e053e129669cf3e896d381e3c0ac01c763edd. Ni limite physique ni calibration terrain.

La valeur numérique explicite reste prioritaire. Les qualificatifs non déclarés demandent une clarification.

### Convention qualitative — `inputs.gradient_percent`

Valeur de scénario proposée, à valider. Le niveau courant reprend le défaut déclaré ; élevé et très élevé utilisent 75 % et 100 % de la référence haute du curseur. Ces niveaux ne sont pas des statistiques observées.

| Expression | Règle | Valeur | Unité ou type |
|---|---|---|---|
| faible | Valeur déclarée | 0.5 | % |
| courant | Valeur déclarée | 2.0 | % |
| élevé | 0.75 × 12.0 | 9.0 | % |
| très élevé | 1.0 × 12.0 | 12.0 | % |

Convention d’essai WebSemantic ; références de curseurs vérifiées dans TLS app.py @748e053e129669cf3e896d381e3c0ac01c763edd. Ni limite physique ni calibration terrain.

La valeur numérique explicite reste prioritaire. Les qualificatifs non déclarés demandent une clarification.

### Interprétation — `inputs.tunnel_context`

Catégories sans ordre universel : utiliser uniquement les catégories déclarées et leurs synonymes non ambigus. « Ancien », « moderne », « fort » ou « faible » seuls demandent une précision ; l’âge ne détermine pas une technologie ni ses performances.

### Interprétation — `inputs.lighting_type`

Catégories sans ordre universel : utiliser uniquement les catégories déclarées et leurs synonymes non ambigus. « Ancien », « moderne », « fort » ou « faible » seuls demandent une précision ; l’âge ne détermine pas une technologie ni ses performances.

### Interprétation — `inputs.ventilation_type`

Catégories sans ordre universel : utiliser uniquement les catégories déclarées et leurs synonymes non ambigus. « Ancien », « moderne », « fort » ou « faible » seuls demandent une précision ; l’âge ne détermine pas une technologie ni ses performances.

### Convention qualitative — `inputs.aux_kw_per_km_tube`

Valeur de scénario proposée, à valider. Le niveau courant reprend le défaut déclaré ; élevé et très élevé utilisent 75 % et 100 % de la référence haute du curseur. Ces niveaux ne sont pas des statistiques observées.

| Expression | Règle | Valeur | Unité ou type |
|---|---|---|---|
| faible | Valeur déclarée | 8.75 | kW/(km·tube) |
| courant | Valeur déclarée | 35.0 | kW/(km·tube) |
| élevé | 0.75 × 120.0 | 90.0 | kW/(km·tube) |
| très élevé | 1.0 × 120.0 | 120.0 | kW/(km·tube) |

Convention d’essai WebSemantic ; références de curseurs vérifiées dans TLS app.py @748e053e129669cf3e896d381e3c0ac01c763edd. Ni limite physique ni calibration terrain.

La valeur numérique explicite reste prioritaire. Les qualificatifs non déclarés demandent une clarification.

### Convention qualitative — `inputs.base_fixed_kw`

Valeur de scénario proposée, à valider. Le niveau courant reprend le défaut déclaré ; élevé et très élevé utilisent 75 % et 100 % de la référence haute du curseur. Ces niveaux ne sont pas des statistiques observées.

| Expression | Règle | Valeur | Unité ou type |
|---|---|---|---|
| faible | Valeur déclarée | 10.0 | kW |
| courant | Valeur déclarée | 40.0 | kW |
| élevé | 0.75 × 500.0 | 375.0 | kW |
| très élevé | 1.0 × 500.0 | 500.0 | kW |

Convention d’essai WebSemantic ; références de curseurs vérifiées dans TLS app.py @748e053e129669cf3e896d381e3c0ac01c763edd. Ni limite physique ni calibration terrain.

La valeur numérique explicite reste prioritaire. Les qualificatifs non déclarés demandent une clarification.

### Convention qualitative — `inputs.traffic_level`

Convention de scénario autorisée pour les essais : fraction de la référence haute 2 ; hypothèse à valider, sans comptage local.

| Expression | Règle | Valeur | Unité ou type |
|---|---|---|---|
| beaucoup | 0.75 × 2.0 | 1.5 | 1 |
| énormément | 1.0 × 2.0 | 2.0 | 1 |
| faible | Valeur déclarée | 0.3 | 1 |
| courant | Valeur déclarée | 1.0 | 1 |

TLS app.py, Global traffic level slider, revision 748e053e129669cf3e896d381e3c0ac01c763edd; upper interface reference, not physical capacity or adapter maximum.

La valeur numérique explicite reste prioritaire. Les qualificatifs non déclarés demandent une clarification.

### Convention qualitative — `inputs.morning_peak_hour`

Centre de la pointe en heures du jour, proposé à valider ; ce n’est pas une durée ni un horaire local observé.

| Expression | Règle | Valeur | Unité ou type |
|---|---|---|---|
| tôt | Valeur déclarée | 5 | h du jour |
| courant | Valeur déclarée | 8 | h du jour |
| tard | Valeur déclarée | 11 | h du jour |

Convention d’essai WebSemantic ; références de curseurs vérifiées dans TLS app.py @748e053e129669cf3e896d381e3c0ac01c763edd. Ni limite physique ni calibration terrain.

La valeur numérique explicite reste prioritaire. Les qualificatifs non déclarés demandent une clarification.

### Convention qualitative — `inputs.evening_peak_hour`

Centre de la pointe en heures du jour, proposé à valider ; ce n’est pas une durée ni un horaire local observé.

| Expression | Règle | Valeur | Unité ou type |
|---|---|---|---|
| tôt | Valeur déclarée | 15 | h du jour |
| courant | Valeur déclarée | 18 | h du jour |
| tard | Valeur déclarée | 22 | h du jour |

Convention d’essai WebSemantic ; références de curseurs vérifiées dans TLS app.py @748e053e129669cf3e896d381e3c0ac01c763edd. Ni limite physique ni calibration terrain.

La valeur numérique explicite reste prioritaire. Les qualificatifs non déclarés demandent une clarification.

### Convention qualitative — `inputs.peak_width_h`

Valeur de scénario proposée, à valider. Le niveau courant reprend le défaut déclaré ; élevé et très élevé utilisent 75 % et 100 % de la référence haute du curseur. Ces niveaux ne sont pas des statistiques observées.

| Expression | Règle | Valeur | Unité ou type |
|---|---|---|---|
| faible | Valeur déclarée | 0.35 | h |
| courant | Valeur déclarée | 1.4 | h |
| élevé | 0.75 × 4.0 | 3.0 | h |
| très élevé | 1.0 × 4.0 | 4.0 | h |

Convention d’essai WebSemantic ; références de curseurs vérifiées dans TLS app.py @748e053e129669cf3e896d381e3c0ac01c763edd. Ni limite physique ni calibration terrain.

La valeur numérique explicite reste prioritaire. Les qualificatifs non déclarés demandent une clarification.

### Convention qualitative — `inputs.traffic_sensitivity`

Valeur de scénario proposée, à valider. Le niveau courant reprend le défaut déclaré ; élevé et très élevé utilisent 75 % et 100 % de la référence haute du curseur. Ces niveaux ne sont pas des statistiques observées.

| Expression | Règle | Valeur | Unité ou type |
|---|---|---|---|
| faible | Valeur déclarée | 0.1625 | 1 |
| courant | Valeur déclarée | 0.65 | 1 |
| élevé | 0.75 × 1.5 | 1.125 | 1 |
| très élevé | 1.0 × 1.5 | 1.5 | 1 |

Convention d’essai WebSemantic ; références de curseurs vérifiées dans TLS app.py @748e053e129669cf3e896d381e3c0ac01c763edd. Ni limite physique ni calibration terrain.

La valeur numérique explicite reste prioritaire. Les qualificatifs non déclarés demandent une clarification.

### Convention qualitative — `inputs.noise_sigma`

Valeur de scénario proposée, à valider. Le niveau courant reprend le défaut déclaré ; élevé et très élevé utilisent 75 % et 100 % de la référence haute du curseur. Ces niveaux ne sont pas des statistiques observées.

| Expression | Règle | Valeur | Unité ou type |
|---|---|---|---|
| faible | Valeur déclarée | 0.015 | 1 |
| courant | Valeur déclarée | 0.06 | 1 |
| élevé | 0.75 × 0.5 | 0.375 | 1 |
| très élevé | 1.0 × 0.5 | 0.5 | 1 |

Convention d’essai WebSemantic ; références de curseurs vérifiées dans TLS app.py @748e053e129669cf3e896d381e3c0ac01c763edd. Ni limite physique ni calibration terrain.

La valeur numérique explicite reste prioritaire. Les qualificatifs non déclarés demandent une clarification.

### Convention qualitative — `inputs.pollution_probability_per_day`

Valeur de scénario proposée, à valider. Le niveau courant reprend le défaut déclaré ; élevé et très élevé utilisent 75 % et 100 % de la référence haute du curseur. Ces niveaux ne sont pas des statistiques observées.

| Expression | Règle | Valeur | Unité ou type |
|---|---|---|---|
| faible | Valeur déclarée | 0.0125 | 1 |
| courant | Valeur déclarée | 0.05 | 1 |
| élevé | 0.75 × 0.5 | 0.375 | 1 |
| très élevé | 1.0 × 0.5 | 0.5 | 1 |

Convention d’essai WebSemantic ; références de curseurs vérifiées dans TLS app.py @748e053e129669cf3e896d381e3c0ac01c763edd. Ni limite physique ni calibration terrain.

La valeur numérique explicite reste prioritaire. Les qualificatifs non déclarés demandent une clarification.

### Convention qualitative — `inputs.accident_probability_per_day`

Valeur de scénario proposée, à valider. Le niveau courant reprend le défaut déclaré ; élevé et très élevé utilisent 75 % et 100 % de la référence haute du curseur. Ces niveaux ne sont pas des statistiques observées.

| Expression | Règle | Valeur | Unité ou type |
|---|---|---|---|
| faible | Valeur déclarée | 0.00375 | 1 |
| courant | Valeur déclarée | 0.015 | 1 |
| élevé | 0.75 × 0.2 | 0.15000000000000002 | 1 |
| très élevé | 1.0 × 0.2 | 0.2 | 1 |

Convention d’essai WebSemantic ; références de curseurs vérifiées dans TLS app.py @748e053e129669cf3e896d381e3c0ac01c763edd. Ni limite physique ni calibration terrain.

La valeur numérique explicite reste prioritaire. Les qualificatifs non déclarés demandent une clarification.

### Convention qualitative — `inputs.pollution_sensitivity`

Valeur de scénario proposée, à valider. Le niveau courant reprend le défaut déclaré ; élevé et très élevé utilisent 75 % et 100 % de la référence haute du curseur. Ces niveaux ne sont pas des statistiques observées.

| Expression | Règle | Valeur | Unité ou type |
|---|---|---|---|
| faible | Valeur déclarée | 0.1375 | 1 |
| courant | Valeur déclarée | 0.55 | 1 |
| élevé | 0.75 × 2.0 | 1.5 | 1 |
| très élevé | 1.0 × 2.0 | 2.0 | 1 |

Convention d’essai WebSemantic ; références de curseurs vérifiées dans TLS app.py @748e053e129669cf3e896d381e3c0ac01c763edd. Ni limite physique ni calibration terrain.

La valeur numérique explicite reste prioritaire. Les qualificatifs non déclarés demandent une clarification.

### Convention qualitative — `inputs.accident_sensitivity`

Valeur de scénario proposée, à valider. Le niveau courant reprend le défaut déclaré ; élevé et très élevé utilisent 75 % et 100 % de la référence haute du curseur. Ces niveaux ne sont pas des statistiques observées.

| Expression | Règle | Valeur | Unité ou type |
|---|---|---|---|
| faible | Valeur déclarée | 0.1875 | 1 |
| courant | Valeur déclarée | 0.75 | 1 |
| élevé | 0.75 × 2.0 | 1.5 | 1 |
| très élevé | 1.0 × 2.0 | 2.0 | 1 |

Convention d’essai WebSemantic ; références de curseurs vérifiées dans TLS app.py @748e053e129669cf3e896d381e3c0ac01c763edd. Ni limite physique ni calibration terrain.

La valeur numérique explicite reste prioritaire. Les qualificatifs non déclarés demandent une clarification.

### Interprétation — `experiment.start_date`

Demander une date ou une référence temporelle explicite. « Tôt », « tard » et « début d’année » sans année ne déterminent pas une date. Ne pas choisir silencieusement la date du jour. Le défaut est une proposition acceptée seulement sur accord.

### Convention qualitative — `experiment.n_days`

Durées conventionnelles en jours : 1, 7, 365 et 1095. Les calculs longs peuvent être plus coûteux ; ces durées ne garantissent pas une couverture calendaire complète.

| Expression | Règle | Valeur | Unité ou type |
|---|---|---|---|
| court | Valeur déclarée | 1 | jours |
| courant | Valeur déclarée | 7 | jours |
| long | Valeur déclarée | 365 | jours |
| très long | Valeur déclarée | 1095 | jours |

Convention d’essai WebSemantic ; références de curseurs vérifiées dans TLS app.py @748e053e129669cf3e896d381e3c0ac01c763edd. Ni limite physique ni calibration terrain.

La valeur numérique explicite reste prioritaire. Les qualificatifs non déclarés demandent une clarification.

### Convention qualitative — `experiment.freq_minutes`

Pas internes admis par TLS, en minutes. Un pas plus fin est plus petit. Une sortie journalière est une agrégation et ne fixe pas ce pas interne.

| Expression | Règle | Valeur | Unité ou type |
|---|---|---|---|
| très fin | Valeur déclarée | 5 | min |
| fin | Valeur déclarée | 10 | min |
| intermédiaire | Valeur déclarée | 15 | min |
| large | Valeur déclarée | 30 | min |
| grossier | Valeur déclarée | 60 | min |

Convention d’essai WebSemantic ; références de curseurs vérifiées dans TLS app.py @748e053e129669cf3e896d381e3c0ac01c763edd. Ni limite physique ni calibration terrain.

La valeur numérique explicite reste prioritaire. Les qualificatifs non déclarés demandent une clarification.

### Convention qualitative — `experiment.n_runs`

Comptages Monte Carlo conventionnels, à valider ; beaucoup = 30 et énormément = 50 selon une échelle entière. Plus de réalisations augmente le coût ; cela ne valide pas le modèle.

| Expression | Règle | Valeur | Unité ou type |
|---|---|---|---|
| peu | Valeur déclarée | 1 | nombre |
| courant | Valeur déclarée | 3 | nombre |
| beaucoup | Valeur déclarée | 30 | nombre |
| maximum de référence | Valeur déclarée | 50 | nombre |

Convention d’essai WebSemantic ; références de curseurs vérifiées dans TLS app.py @748e053e129669cf3e896d381e3c0ac01c763edd. Ni limite physique ni calibration terrain.

La valeur numérique explicite reste prioritaire. Les qualificatifs non déclarés demandent une clarification.

### Interprétation — `experiment.base_seed`

Identifiant technique fixe à 42 par autorisation antérieure, modifiable uniquement sur demande explicite chiffrée. Faible, forte, meilleure ou nouvelle graine ne désignent pas une intensité physique ; demander une valeur. Ne pas proposer de graine qualitative.

## Comparer deux scénarios

Deux exécutions indépendantes après validation complète. CSV réunis avec une colonne scenario valant scenario_1 ou scenario_2 ; aucune moyenne entre scénarios. Conserver les sorties et manifestes individuels. Écarts entre médianes ; pourcentage relatif au scénario 2, indéfini si référence nulle. Graines communes, sans garantie de tirages identiques après modification de configuration.

Champs contrôlés identiques : experiment.start_date, experiment.n_days, experiment.freq_minutes, experiment.n_runs, experiment.base_seed.

La longueur ou les équipements manquants du second cas ne sont pas copiés sans instruction explicite. Chaque hypothèse est validée par scénario.


## Formules du modèle

### Trafic

`T(t) = clip((R(t)/Q98) × C × S × W × traffic_level × D_j, 0, 2)` — sans unité

R est le profil de pointes et de nuit ; Q98 est sa référence déterministe au 98e percentile, C le contexte, S la saison, W le jour de semaine et D_j un tirage journalier normal de moyenne 1 et écart-type 0,06. Aucun comptage de véhicules.

TLS simulator.py:simulate_one_realization / run_monte_carlo, commit 748e053e129669cf3e896d381e3c0ac01c763edd.

### Pointes

`G(h;c,w,A) = A × exp(-0,5 × ((h-c)/w)^2)` — sans unité

h, c et w sont en heures ; A est sans unité. R = 0,16 + 0,06 cos(2π(h-3)/24) + G(h;c_m,w,1) + G(h;c_s,1,15w,1,1), plus G(h;18,7;2,5;0,25) en contexte urbain. w est un écart-type temporel.

TLS simulator.py:simulate_one_realization / run_monte_carlo, commit 748e053e129669cf3e896d381e3c0ac01c763edd.

### Facteurs géométriques

`F_alt = 1 + max(altitude_m-500,0)/6000 ; F_pente = 1 + abs(gradient_percent)/20 ; F_profondeur = 1 + min(max_depth_m,800)/6000` — sans unité

Altitude et profondeur en m ; pente saisie en %, donc 2 pour 2 %. Le plafond de profondeur concerne le facteur, pas la longueur ni la validité géologique.

TLS simulator.py:simulate_one_realization / run_monte_carlo, commit 748e053e129669cf3e896d381e3c0ac01c763edd.

### Éclairage

`P_lumière(t) = k_l × L × N_tubes × N_voies × min(f_min + (1-f_min)(1-J(t)) + c_l T(t), 1)` — kW

L = length_m/1000 en km. k_l en kW/(km·voie), f_min et c_l sans unité dépendent de la catégorie. J(t) est le profil synthétique de lumière du jour, sans éphéméride locale ; même une catégorie fixed est modulée.

TLS simulator.py:simulate_one_realization / run_monte_carlo, commit 748e053e129669cf3e896d381e3c0ac01c763edd.

### Ventilation

`P_vent(t) = k_v × L × N_tubes × (0,15 + traffic_sensitivity × T(t)) × F_alt × F_pente × (1 + pollution_sensitivity × I_p(t) + accident_sensitivity × I_a(t))` — kW

k_v est en kW/(km·tube). I_p et I_a sont des indicateurs 0/1 d’événements synthétiques. Les deux coefficients s’ajoutent si les deux événements sont actifs ; ce n’est pas un modèle de sécurité.

TLS simulator.py:simulate_one_realization / run_monte_carlo, commit 748e053e129669cf3e896d381e3c0ac01c763edd.

### Auxiliaires

`P_aux(t) = aux_kw_per_km_tube × L × N_tubes × F_profondeur × Z(t)` — kW

Z(t) suit une loi normale de moyenne 1 et d’écart-type 0,025 ; ce tirage reste actif même si noise_sigma vaut zéro.

TLS simulator.py:simulate_one_realization / run_monte_carlo, commit 748e053e129669cf3e896d381e3c0ac01c763edd.

### Puissance totale

`P(t) = max((base_fixed_kw + P_lumière(t) + P_vent(t) + P_aux(t)) × (1 + ε(t)), 0)` — kW

ε suit une loi normale de moyenne zéro et d’écart-type noise_sigma. La graine fixe rend les trajectoires reproductibles, sans supprimer les tirages.

TLS simulator.py:simulate_one_realization / run_monte_carlo, commit 748e053e129669cf3e896d381e3c0ac01c763edd.

### Énergie et annualisation

`E_pas = P(t) × freq_minutes/60 ; E_MWh = somme(E_pas)/1000 ; E_ann = E_MWh × 365/n_days` — kWh ; MWh ; MWh/an

L’énergie journalière somme les pas d’une journée. La puissance quotidienne est la moyenne des puissances. E_ann est une extrapolation de la période simulée ; aucune mesure annuelle terrain.

TLS simulator.py:simulate_one_realization / run_monte_carlo, commit 748e053e129669cf3e896d381e3c0ac01c763edd.

### Événements

`B_j ~ Bernoulli(p) ; I(t) = 1 pendant l’événement si B_j = 1` — probabilité sans unité ; durée en h

p est la probabilité journalière déclarée, pas un taux par véhicule. Pollution : début uniforme de 7 à 18 h, durée de 2 à 8 h. Accident : début de 6,5 à 20 h, durée de 0,5 à 3 h. Un événement peut déborder sur le lendemain.

TLS simulator.py:simulate_one_realization / run_monte_carlo, commit 748e053e129669cf3e896d381e3c0ac01c763edd.

### Coefficients des catégories

| Éclairage | k_l [kW/(km·voie)] | c_l [1] | f_min [1] |
|---|---|---|---|
| LED adaptive | 16 | 0.18 | 0.2 |
| LED fixed | 22 | 0.06 | 0.28 |
| mixed | 28 | 0.04 | 0.32 |
| sodium fixed | 35 | 0.03 | 0.4 |

| Ventilation | k_v [kW/(km·tube)] |
|---|---|
| natural/low ventilation | 45 |
| longitudinal | 120 |
| semi-transverse | 200 |
| transverse | 320 |

Facteurs `context` sans unité : urban=1.2, peri-urban=1.0, rural=0.78.

Facteurs `season` sans unité : winter=1.12, spring=0.98, summer=0.92, autumn=1.03.

Facteurs `weekday` sans unité : weekday=1.0, saturday=0.86, sunday=0.78.

## Sorties

Les quantités concernent tous les tubes. Les séries ne déclarent pas de fuseau horaire.

### representative.csv

Réalisation 0 au pas natif ; exemple de trajectoire, pas la médiane.

| Colonne | Unité | Sens |
|---|---|---|
| `timestamp` | ISO 8601 | Horodatage sans fuseau horaire déclaré ; aucune localisation déduite. |
| `season` | sans unité | Saison du calendrier simulé ; ne prouve pas une couverture annuelle. |
| `hour_int` | h | Heure du jour, de 0 à 23 ; pas une durée. |
| `dayofweek` | 1 | Indice : lundi 0, dimanche 6. |
| `day_type` | sans unité | Jour de semaine ou week-end du calendrier simulé. |
| `traffic_index` | 1 | Indice relatif de trafic ; pas un nombre de véhicules par jour. |
| `pollution_event` | 1 | Indicateur binaire d'événement de pollution simulé. |
| `accident_event` | 1 | Indicateur binaire d'accident simulé. |
| `lighting_kw` | kW | Puissance électrique calculée. |
| `ventilation_kw` | kW | Puissance électrique calculée. |
| `auxiliary_kw` | kW | Puissance électrique calculée. |
| `power_kw` | kW | Puissance électrique calculée. |
| `energy_kwh` | kWh | Énergie du pas : power_kw × freq_minutes / 60. |

### kpis.csv

Une ligne par réalisation sur toute la période simulée.

| Colonne | Unité | Sens |
|---|---|---|
| `run` | sans unité | Identifiant de réalisation Monte Carlo, à partir de 0. |
| `seed` | sans unité | Graine pseudo-aléatoire : base_seed + run. |
| `total_mwh` | MWh | Énergie de toute la période : somme des energy_kwh / 1000. |
| `annualized_mwh` | MWh/an | Extrapolation : total_mwh × 365 / n_days ; pas une année observée. |
| `peak_kw` | kW | Puissance électrique calculée. |
| `mean_kw` | kW | Puissance électrique calculée. |
| `load_factor` | 1 | mean_kw / peak_kw par réalisation ; sans dimension, 0,6 équivaut à 60 %. |
| `specific_kwh_m_year` | kWh/(m·an) | annualized_mwh × 1000 / length_m ; ensemble des tubes, par mètre de longueur du tunnel, pas par mètre-tube. |
| `n_pollution_events` | 1 | Nombre de transitions 0 vers 1 dans la série pollution_event ; un événement actif au premier pas n'est pas compté. |
| `n_accident_events` | 1 | Nombre de transitions 0 vers 1 dans la série accident_event ; un événement actif au premier pas n'est pas compté. |
| `base_seed` | sans unité | Graine de base fixe de l’expérience ; 42 par défaut, modifiable explicitement. |

### envelope.csv

Puissances moyennées par heure dans chaque réalisation, puis statistiques entre réalisations. p10/p90 sont des quantiles empiriques, pas un intervalle de confiance.

| Colonne | Unité | Sens |
|---|---|---|
| `timestamp` | ISO 8601 | Horodatage sans fuseau horaire déclaré ; aucune localisation déduite. |
| `median` | kW | Puissance électrique calculée. |
| `p10` | kW | Puissance électrique calculée. |
| `p90` | kW | Puissance électrique calculée. |
| `mean` | kW | Puissance électrique calculée. |

### season_profiles.csv

Puissance moyenne par saison et heure du jour, dans chaque réalisation, uniquement sur les jours simulés.

| Colonne | Unité | Sens |
|---|---|---|
| `season` | sans unité | Saison du calendrier simulé ; ne prouve pas une couverture annuelle. |
| `hour_int` | h | Heure du jour, de 0 à 23 ; pas une durée. |
| `power_kw` | kW | Puissance électrique calculée. |
| `run` | sans unité | Identifiant de réalisation Monte Carlo, à partir de 0. |

### daily.csv

Agrégation journalière de la réalisation 0 : somme de l'énergie et moyenne de la puissance ; pas une médiane Monte Carlo. Les dates suivent le calendrier sans fuseau déclaré.

| Colonne | Unité | Sens |
|---|---|---|
| `timestamp` | ISO 8601 | Horodatage sans fuseau horaire déclaré ; aucune localisation déduite. |
| `energy_kwh` | kWh | Somme des énergies des pas natifs de la journée, réalisation 0. |
| `mean_kw` | kW | Moyenne des puissances des pas natifs de la journée, réalisation 0. |

## Contrôles complémentaires

- Pinned simulator module verified by SHA-256 (LF); Git checks when checkout available
- freq_minutes in 5,10,15,30,60
- n_days * 1440 / freq_minutes * n_runs <= 2000000
- peak_width_h > 0
- 0 <= morning_peak_hour, evening_peak_hour < 24
- Nonnegative max_depth_m, gradient_percent, aux_kw_per_km_tube, base_fixed_kw, traffic_level, traffic_sensitivity, pollution_sensitivity, accident_sensitivity

Ces contraintes du prototype ne constituent pas des limites de validité physique calibrées. Voir docs/agent-contract.md pour les règles d'interprétation et de restitution.
