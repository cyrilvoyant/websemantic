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

## LQL-Equiv

Original code: https://github.com/cyrilvoyant/LQL-Equiv-web (pinned revision in `descriptors/lqlequiv/descriptor.yaml`).

Supported: simulate fictitious radiobiological fractionation; compare fictitious schedules for one target, a list of targets or an anatomical group (compare_schedules). Out of scope: any treatment decision for a patient.

| Field | Unit or categories | Bounds | Default (proposal only) | Meaning |
|---|---|---|---|---|
| `organ` | categories: Temporomandibular joint, Rib cage, Oral cavity / oropharynx, Brain, Optic chiasm, Heart, Colon, Stomach, Liver, Small bowel, Larynx / supraglottis, Spinal cord, Oral mucosa, Muscle / vasculature / cartilage, Optic nerve, Eye, Oesophagus, Middle / external ear, Parotid, Skin (acute), Skin (late), Brachial plexus, Lung, Cauda equina, Rectum, Kidney, Retina, Testis, Femoral head, Thyroid, Brainstem, Bladder, Standard acute-responding tissue, Standard late-responding tissue |  |  | Nom exact dans la bibliothèque radiobiologique ; ne définit pas un patient. |
| `tumour_site` | categories: Tonsil, Carcinoma, Cervix (LQ-L), Vocal cord, Glioblastoma (LQ-L), Larynx, Liposarcoma, Medulloblastoma (LQ-L), Oral mucosa, Nasopharynx, Oesophagus, Oropharynx, Skin carcinoma, Skin melanoma (LQ-L), Lung, Prostate, Rectum, Breast carcinoma, Standard tumour, Standard tumour, no proliferation |  |  | Nom exact dans la bibliothèque ; cas fictif uniquement. |
| `dose_per_fraction` | unit:GRAY | min_exclusive 0 |  | Dose physique pour chaque fraction du seul cursus. |
| `n_fractions` | unit:NUM | min 1 |  | Nombre entier de fractions du seul cursus. |
| `gap_days` | unit:DAY | min 0 | 0 | Intervalle avant le cursus en jours, dans la convention calendaire native. |
| `reference_dose` | unit:GRAY | min_exclusive 0 | 2 | Dose physique par fraction du régime auquel EQD se rapporte ; EQD2 seulement si 2 Gy. |
| `bifractionated` | categories: yes, no |  | no | yes active deux fractions par jour et un intervalle natif fixe de 6 h ; no sinon. |
| `scenario_scope` | categories: fictitious |  | fictitious | Scénario fictif de recherche, sans décision clinique. |

**Qualitative conventions** (propose the value, then ask for acceptance):

| Expression | Field | Proposed value |
|---|---|---|
| « fractionnement conventionnel », « dose conventionnelle » | `dose_per_fraction` | 2 unit:GRAY |

**Clarify, never convert:** « hypofractionnement modéré / extrême », « stéréotaxique », « hyperfractionnement », « dose élevée », « peu de séances ».

**Qualitative policy:** Pour LQL-Equiv, toute expression qualitative de dose, de nombre de séances ou de fractionnement (sauf « fractionnement conventionnel » = 2 Gy proposé) conduit à une question ; aucune valeur n'est proposée ni devinée. Peu de paramètres, conséquences fortes (NTCP de 3 % à 47 % selon la dose lue pour « hypofractionnement modéré » en 20 séances).

**Task `compare_schedules`** — Comparer deux schémas fictifs (ou plus) pour une cible, une liste de cibles ou un groupe anatomique. Scope: une ligne par cible et par schéma ; même organe à risque, même dose de référence pour tous les schémas.

Criterion: Un schéma est dit meilleur pour une cible seulement s'il la domine (TCP supérieur ou égal ET NTCP inférieur ou égal, avec au moins une inégalité stricte). Sinon, compromis, à expliciter avec les valeurs. Jamais de recommandation clinique.

Admissible decisions: deux schémas entièrement spécifiés -> exécuter les deux; organe à risque absent -> demander (jamais choisi par le groupe); dose qualitative -> demander; patient nommé ou décision de traitement -> refuser; TCP ou NTCP non défini dans la bibliothèque pour une cible -> aucun verdict pour cette cible, le dire; cas le plus fréquent (dose plus forte = TCP et NTCP plus élevés) -> compromis, valeurs à l'appui.

**Anatomical groups** (study convention over exact library names; a group never selects the organ at risk):

| Group | Expressions | Tumour sites | Organs |
|---|---|---|---|
| `thoracic` (Thorax (cibles et organes thoraciques)) | « thoracique », « thorax », « cibles thoraciques », « volumes cibles thoraciques » | Lung, Oesophagus, Breast carcinoma | Heart, Lung, Oesophagus, Spinal cord, Brachial plexus, Rib cage |
| `head_and_neck` (Tête et cou (ORL)) | « ORL », « tête et cou », « cervico-facial » | Tonsil, Vocal cord, Larynx, Oral mucosa, Nasopharynx, Oropharynx | Temporomandibular joint, Oral cavity / oropharynx, Larynx / supraglottis, Oral mucosa, Parotid, Middle / external ear, Thyroid |
| `central_nervous_system` (Système nerveux central) | « cérébral », « encéphale », « SNC », « neuro » | Glioblastoma (LQ-L), Medulloblastoma (LQ-L) | Brain, Brainstem, Optic chiasm, Optic nerve, Eye, Retina, Spinal cord |
| `pelvis` (Pelvis) | « pelvien », « pelvis », « petit bassin » | Prostate, Rectum, Cervix (LQ-L) | Rectum, Bladder, Femoral head, Testis, Small bowel, Colon, Cauda equina |
| `abdomen` (Abdomen) | « abdominal », « abdomen » | — | Stomach, Liver, Kidney, Small bowel, Colon |
| `skin` (Peau) | « cutané », « peau » | Skin carcinoma, Skin melanoma (LQ-L) | Skin (acute), Skin (late) |
