"""WebSemantic in the browser (Pyodide): the deterministic half of each conversation turn.

Only the original, validated codes compute (TLS, LQL-Equiv, pinned and sha256-checked through the reviewed adapters).
The language model only translates the visitor's message into variables of the contract; here, locally:
- nothing is accepted on the visitor's behalf; a calculation starts only on a pure confirmation ("yes", "compute"),
  never in the same turn as a change, a restriction, a request to wait or a question;
- every translated value is checked: exact parameter names only, numbers present in the quoted words, declared
  conventions and defaults taken from the descriptor (never a number chosen by the model);
- anything that cannot be used blocks the calculation and is explained;
- if the message could not be read, nothing changes.
"""

import json
import math
import os
import re
import shutil
import tempfile
import unicodedata
from pathlib import Path

import pandas as pd

from websemantic import lql_workbench as wb
from websemantic.adapters.lql import _backend
from websemantic.core.validation import Parameter, Scenario, validate
from websemantic.qualitative import resolve
from websemantic.registry import execute, load_descriptor
from websemantic.units import NUMBER_WORDS, normalize, parse_number

WS = Path(os.environ.get("WEBSEMANTIC_WS", "/home/pyodide/ws"))
CODES = ("tls", "lql")
DESC = {m: load_descriptor(WS, m) for m in CODES}
SINGLE_TASK = {m: DESC[m]["tasks"]["supported"][0] for m in CODES}
MAX_DAYS, MAX_RUNS, MAX_POINTS = 366, 10, 366 * 96 * 10  # one year at 15 min, 10 runs: keeps the browser responsive
NBSP = chr(0x00A0)
NAME = re.compile(r"^[a-z_][a-z0-9_]*$")

T = {
    "en": {
        "explain": {"missing": "no value yet", "unaccepted_assumption": "proposed, waiting for your agreement",
                    "unsupported_origin": "origin not allowed", "evidence": "quote not found in your message",
                    "unit": "not the canonical unit", "bounds": "outside the declared bounds",
                    "category": "not an allowed category", "type": "wrong type", "finite": "must be finite",
                    "unknown_field": "not a parameter of this code", "conflict": "conflicting values",
                    "unsupported_task": "outside what the code supports"},
        "computed": "The pinned code has run on the accepted values. Results are on the right.",
        "refused": "This message is outside what the code does: nothing is computed or changed.",
        "refused_ongoing": "The current case is unchanged: reply **yes** to compute it, change a value, or click **New conversation** for a new case.",
        "refused_hint": {"tls": "TLS simulates fictitious tunnels from stated assumptions; it neither measures nor predicts the real consumption of an existing tunnel and certifies nothing. You can ask, for example: “a 3 km tunnel, two tubes, over one year”.",
                         "lql": "LQL-Equiv gives model outputs for fictitious schedules; it makes no treatment decision for a patient. You can ask, for example: “equivalent dose of 20 sessions of 3 Gy for the prostate, rectum as organ at risk”."},
        "not_here": "This kind of request (for instance a comparison of several schedules) is not available on this "
                    "page. Nothing was changed or computed.",
        "needed": "Still needed: **{}**.",
        "conventions": "From your words I propose {}.",
        "defaults": "The other {} parameters take the code's default values (see Variables).",
        "pending": "Reply **yes** to accept everything, or give your own values. Nothing is computed before that.",
        "ready": "Everything is stated or accepted. Reply **yes** to run the calculation.",
        "accepted_some": "Accepted: {}. The other proposals are still waiting.",
        "noted": "Noted from your words: {}.",
        "unchanged": "No value was changed by this message.",
        "gap_short": "{} days break",
        "ask_choose": "Two schedules: should I compute them **one after the other** (successive courses) or **compare** them as alternatives?",
        "unparsed": "I did not recognise “{}” as a schedule: please write it as, for example, 20 × 3.5 Gy.",
        "plan_sequence": "Successive courses: **{}**; cumulated effect for the tumour and the organs at risk {}.",
        "after_gap": "after {} days", "then": ", then ",
        "answer_sequence": "Answer: {chain} → cumulated EQD2 **{eqt} Gy for the tumour** (TCP {tcp} %). Organs at risk: {organs}.",
        "col_course": "course {}: {} (EQD2, Gy)", "col_total": "total",
        "chart_sequence": "EQD2 of each course and in total (Gy)",
        "k_courses": "courses", "k_physical": "total physical dose (Gy)",
        "explain_sequence": "How to read: each column is one course, in order, with the interruption before it; the cells give its EQD2 contribution (it may be negative after a long interruption, because the model counts repopulation) and the last column the cumulated EQD2, TCP and NTCP computed by LQL-Equiv for the whole prescription.",
        "plan_minimum": "Same tumour effect as **{}** for several numbers of sessions, and the EQD2 it gives to the organs at risk {}.",
        "answer_minimum": "Answer: for the same tumour effect as {ref}, the organs at risk are least exposed with **{n} sessions of {d} Gy** (most exposed organ: {w} % of its EQD2 with {ref}). Best number of sessions for each organ: {per}.",
        "chart_minimum": "Organs' EQD2 with the tumour-equivalent dose, relative to the reference schedule (%), by number of sessions",
        "k_best_sessions": "best number of sessions", "k_best_dose": "tumour-equivalent dose (Gy per session)",
        "k_worst_organ": "most exposed organ vs reference (%)", "k_cases": "numbers of sessions examined",
        "explain_minimum": "How to read: each column is a number of sessions with the tumour dose that keeps the reference tumour effect (LQL-Equiv); each organ's cell gives the EQD2 it then receives and the difference from the reference schedule. Negative = less than with the reference. Simulation: the practitioner decides in the clinical context.",
        "organs_noted": "Organs at risk: **{}** (one LQL-Equiv calculation per organ).",
        "group_none": "To list all the organs at risk, give the tumour site first (its anatomical group comes from the ontology).",
        "group_proposed": "Organs at risk of the anatomical group **{}** (from the ontology): **{}**. One LQL-Equiv calculation per organ.",
        "organs_dropped": "The organ(s) at risk of the previous case ({}) do not belong to the anatomical group of {} ({}): please give the organs at risk of this case.",
        "ask_gap": "How many days did the interruption last?",
        "ask_done": "How many sessions have already been given?",
        "ask_done_ambiguous": "“At session {0}”: {1} sessions already given (session {0} comes next), or {2}?",
        "ask_remaining": "How many sessions are still possible? (or say “the same number of sessions”)",
        "ask_target": "Over how many sessions?",
        "plan_compare": "I will compare **{}** for the organs at risk {}.",
        "plan_resume": "Resumption: **{}** planned, {} sessions given, {} days of interruption, **{} sessions** remaining; organs at risk: {}.",
        "plan_maximum": "Highest dose per session over **{} sessions** that exceeds, for no organ at risk, the EQD2 of **{}**; organs: {}.",
        "col_tissue": "tissue", "target": "tumour",
        "answer_table": "Answer: {}. Organs at risk: {}.",
        "see_table": "see the table, schedule by schedule",
        "chart_eqd2": "EQD2 of each tissue (Gy)",
        "k_eqd_target": "tumour EQD2 (Gy)", "k_organs": "organs at risk", "k_schedules": "schedules",
        "answer_resume": "Answer: to give back the planned tumour EQD2 ({eqd} Gy), the **{n} remaining sessions should be {d} Gy each**. Without compensation ({dp} Gy per session), the tumour loses {loss} %. To exceed no organ's planned EQD2, the highest dose per session is **{m} Gy** (limited by {lim}).",
        "col_planned_eqd2": "planned EQD2 (Gy)", "col_n_sessions": "{} sessions",
        "row_max": "highest dose, all organs",
        "chart_resume": "Equivalent dose per session for {} remaining sessions (Gy)",
        "series_equivalent": "equivalent dose per session",
        "line_max": "highest dose, all organs",
        "k_dose_resume": "tumour: Gy per session ({} sessions)", "k_max_dose": "highest dose, all organs (Gy)",
        "k_loss": "tumour loss without compensation (%)", "k_planned_eqd2": "planned tumour EQD2 (Gy)",
        "answer_maximum": "Answer: over {n} sessions, the highest dose that exceeds, for no organ at risk, the EQD2 of {ref} is **{m} Gy per session** (limited by {lim}). For the tumour, the equivalent of {ref} would be {dt} Gy per session.",
        "col_ref_eqd2": "EQD2 with {} (Gy)", "col_equiv_dose": "equivalent dose, {} sessions",
        "chart_maximum": "Equivalent dose per session over {} sessions (Gy)",
        "k_limiting": "limiting organ", "k_tumour_equiv": "tumour equivalent (Gy per session)", "k_sessions": "sessions",
        "explain_simulate": "How to read: EQD2 is the dose that, given in 2 Gy sessions, would have the same biological effect; each tissue has its own, because tissues respond differently to the dose per session. TCP and NTCP are model probabilities for this fictitious scenario.",
        "explain_compare": "How to read: one column per schedule. Compare the tumour EQD2 and TCP with each organ's EQD2 and NTCP: a schedule is better for a tissue only if it dominates (higher TCP and lower NTCP); otherwise it is a trade-off.",
        "explain_resume": "How to read: one column per possible number of remaining sessions; each cell is the dose per session that gives back that tissue's planned EQD2 (LQL-Equiv, 0.01 Gy steps). The last row is the highest dose that keeps every organ within its planned EQD2. Simulation: the practitioner decides in the clinical context.",
        "explain_maximum": "How to read: for each organ, the dose per session that gives the same EQD2 as the reference schedule; the smallest of them is the highest dose that exceeds no organ. Simulation: the practitioner decides in the clinical context.",
        "answer_tls": "Answer: this tunnel would use about **{ann} MWh per year**, with a peak of **{peak} kW** around {hour}:00; ventilation takes {ve} % of the energy, lighting {li} % and auxiliaries {au} %{extra}.",
        "tls_extrapolated": " (extrapolated from {} simulated days)",
        "answer_lql": "Answer: {phys} Gy physical correspond to an EQD2 of **{eqt} Gy for the tumour** (TCP {tcp} %) and **{eqo} Gy for {organ}** (NTCP {ntcp} %).",
        "new_case": "Several values you had given were replaced. If this is a new case, click **New conversation** to start from scratch.",
        "blocked": "Still unresolved: **{}** (your last request for it could not be applied). Give the value you want, "
                   "or say **keep** to leave the current value; nothing is computed before that.",
        "kept": "Understood: {} keeps its current value.",
        "not_named": " — this parameter was not named in your message: please check",
        "held": "Understood: nothing is computed for now.",
        "fix": "To fix: {}.",
        "unused": "I could not use: {}. Nothing is computed until this is clarified.",
        "unread": "I could not read your message right now (language service busy or unavailable). Nothing was changed "
                  "or computed; please try again, or reply **yes** to confirm the scenario already shown.",
        "limit": "In the browser, simulations are limited to {} days, {} Monte Carlo runs and about {:,} time points: "
                 "please reduce the period or the number of runs.",
        "failed_run": "The code refused this scenario: {}",
        "example_done": "Example computed without the language model: every value is stated and accepted (see Variables).",
        "not_computable": "not computable",
        "status": ("stated by you", "accepted", "proposed, to accept"),
        "period": "Default period in the browser (7 days, 5 runs); change it in the chat (up to one year, 10 runs)",
        "tls_analysis": "Over {days} simulated days the median peak power is {peak:,.0f} kW and the mean {mean:,.0f} kW "
                        "(load factor {lf:.2f}); the representative run peaks around {hour}:00. In that run, energy "
                        "splits into lighting {li:.0f} %, ventilation {ve:.0f} % and auxiliaries {au:.0f} %. The 10–90 % "
                        "band between Monte Carlo runs has a mean width of {band:.0f} % of the median. ",
        "annual_extrapolated": "The annual figure ({ann:,.0f} MWh/yr) extrapolates the period by 365/{days}; it is not "
                               "a seasonally complete year.",
        "annual_full": "The annual figure ({ann:,.0f} MWh/yr) comes from a simulated year with its seasons.",
        "lql_analysis": "A physical dose of {phys} Gy corresponds to an EQD2 of {eqt} Gy for the target and {eqo} Gy "
                        "for the organ at risk, over {days} days. The model gives a tumour control probability of {tcp} % "
                        "and a complication probability of {ntcp} %. These are model outputs for a fictitious scenario "
                        "with the parameters of the code's library; they do not support any clinical decision.",
    },
    "fr": {
        "explain": {"missing": "pas encore de valeur", "unaccepted_assumption": "proposé, en attente de votre accord",
                    "unsupported_origin": "origine non admise", "evidence": "citation absente de votre message",
                    "unit": "pas l'unité canonique", "bounds": "hors des bornes déclarées",
                    "category": "catégorie non admise", "type": "type incorrect", "finite": "doit être fini",
                    "unknown_field": "pas un paramètre de ce code", "conflict": "valeurs contradictoires",
                    "unsupported_task": "hors du périmètre du code"},
        "computed": "Le code figé a tourné sur les valeurs acceptées. Les résultats sont à droite.",
        "refused": "Ce message sort de ce que fait le code : rien n'est calculé ni modifié.",
        "refused_ongoing": "Le cas en cours est inchangé : répondez **oui** pour le calculer, modifiez une valeur, ou cliquez sur **Nouvelle conversation** pour un nouveau cas.",
        "refused_hint": {"tls": "TLS simule des tunnels fictifs à partir d'hypothèses ; il ne mesure ni ne prédit la consommation réelle d'un tunnel existant et ne certifie rien. Vous pouvez demander par exemple : « un tunnel de 3 km, deux tubes, sur un an ».",
                         "lql": "LQL-Equiv donne des sorties de modèle pour des schémas fictifs ; il ne décide d'aucun traitement pour un patient. Vous pouvez demander par exemple : « dose équivalente de 20 séances de 3 Gy pour la prostate, rectum comme organe à risque »."},
        "not_here": "Ce type de demande (par exemple une comparaison de plusieurs schémas) n'est pas disponible sur "
                    "cette page. Rien n'a été modifié ni calculé.",
        "needed": "Il manque encore : **{}**.",
        "conventions": "D'après vos mots, je propose {}.",
        "defaults": "Les {} autres paramètres reprennent les valeurs par défaut du code (voir Variables).",
        "pending": "Répondez **oui** pour tout accepter, ou donnez vos propres valeurs. Rien n'est calculé avant.",
        "ready": "Tout est donné ou accepté. Répondez **oui** pour lancer le calcul.",
        "accepted_some": "Accepté : {}. Les autres propositions restent en attente.",
        "noted": "Noté d'après vos mots : {}.",
        "unchanged": "Ce message n'a changé aucune valeur.",
        "gap_short": "arrêt de {} jours",
        "ask_choose": "Deux schémas : faut-il les calculer **l'un après l'autre** (cures successives) ou les **comparer** comme alternatives ?",
        "unparsed": "Je n'ai pas reconnu « {} » comme un schéma : écrivez-le par exemple 20 × 3,5 Gy.",
        "plan_sequence": "Cures successives : **{}** ; effet cumulé pour la tumeur et les organes à risque {}.",
        "after_gap": "après {} jours", "then": ", puis ",
        "answer_sequence": "Réponse : {chain} → EQD2 cumulée **{eqt} Gy pour la tumeur** (TCP {tcp} %). Organes à risque : {organs}.",
        "col_course": "cure {} : {} (EQD2, Gy)", "col_total": "total",
        "chart_sequence": "EQD2 de chaque cure et au total (Gy)",
        "k_courses": "cures", "k_physical": "dose physique totale (Gy)",
        "explain_sequence": "Comment lire : chaque colonne est une cure, dans l'ordre, avec l'arrêt qui la précède ; les cases donnent sa contribution en EQD2 (elle peut être négative après un long arrêt, car le modèle compte la repopulation) et la dernière colonne l'EQD2 cumulée, le TCP et le NTCP calculés par LQL-Equiv pour toute la prescription.",
        "plan_minimum": "Même effet tumoral que **{}** pour plusieurs nombres de séances, et l'EQD2 qui en résulte pour les organes à risque {}.",
        "answer_minimum": "Réponse : pour le même effet tumoral que {ref}, les organes à risque sont le moins exposés avec **{n} séances de {d} Gy** (organe le plus exposé : {w} % de son EQD2 avec {ref}). Meilleur nombre de séances pour chaque organe : {per}.",
        "chart_minimum": "EQD2 des organes avec la dose tumorale équivalente, par rapport au schéma de référence (%), selon le nombre de séances",
        "k_best_sessions": "meilleur nombre de séances", "k_best_dose": "dose équivalente tumeur (Gy par séance)",
        "k_worst_organ": "organe le plus exposé / référence (%)", "k_cases": "nombres de séances examinés",
        "explain_minimum": "Comment lire : chaque colonne est un nombre de séances avec la dose tumorale qui garde l'effet tumoral de référence (LQL-Equiv) ; chaque case d'organe donne l'EQD2 qu'il reçoit alors et l'écart avec le schéma de référence. Négatif = moins qu'avec la référence. Simulation : le praticien décide dans le contexte clinique.",
        "organs_noted": "Organes à risque : **{}** (un calcul LQL-Equiv par organe).",
        "group_none": "Pour lister tous les organes à risque, donnez d'abord le site tumoral (son groupe anatomique vient de l'ontologie).",
        "group_proposed": "Organes à risque du groupe anatomique **{}** (ontologie) : **{}**. Un calcul LQL-Equiv par organe.",
        "organs_dropped": "Le ou les organes à risque du cas précédent ({}) n'appartiennent pas au groupe anatomique de {} ({}) : indiquez les organes à risque de ce cas.",
        "ask_gap": "Combien de jours a duré l'interruption ?",
        "ask_done": "Combien de séances ont déjà été faites ?",
        "ask_done_ambiguous": "« À la {0}e séance » : {1} séances déjà faites (la {0}e est la prochaine), ou {2} ?",
        "ask_remaining": "Combien de séances restent possibles ? (ou dites « le même nombre de séances »)",
        "ask_target": "En combien de séances ?",
        "plan_compare": "Je vais comparer **{}** pour les organes à risque {}.",
        "plan_resume": "Reprise : **{}** prévues, {} séances faites, {} jours d'interruption, **{} séances** restantes ; organes à risque : {}.",
        "plan_maximum": "Dose maximale par séance en **{} séances** sans dépasser, pour aucun organe à risque, l'EQD2 de **{}** ; organes : {}.",
        "col_tissue": "tissu", "target": "tumeur",
        "answer_table": "Réponse : {}. Organes à risque : {}.",
        "see_table": "voir le tableau, schéma par schéma",
        "chart_eqd2": "EQD2 de chaque tissu (Gy)",
        "k_eqd_target": "EQD2 tumeur (Gy)", "k_organs": "organes à risque", "k_schedules": "schémas",
        "answer_resume": "Réponse : pour retrouver l'EQD2 prévue de la tumeur ({eqd} Gy), les **{n} séances restantes doivent être de {d} Gy chacune**. Sans compensation ({dp} Gy par séance), la tumeur perd {loss} %. Pour ne dépasser l'EQD2 prévue d'aucun organe, la dose maximale par séance est **{m} Gy** (limitée par {lim}).",
        "col_planned_eqd2": "EQD2 prévue (Gy)", "col_n_sessions": "{} séances",
        "row_max": "dose maximale, tous organes",
        "chart_resume": "Dose équivalente par séance pour {} séances restantes (Gy)",
        "series_equivalent": "dose équivalente par séance",
        "line_max": "dose maximale, tous organes",
        "k_dose_resume": "tumeur : Gy par séance ({} séances)", "k_max_dose": "dose maximale, tous organes (Gy)",
        "k_loss": "perte tumeur sans compensation (%)", "k_planned_eqd2": "EQD2 tumeur prévue (Gy)",
        "answer_maximum": "Réponse : en {n} séances, la dose maximale qui ne dépasse, pour aucun organe à risque, l'EQD2 de {ref} est **{m} Gy par séance** (limitée par {lim}). Pour la tumeur, l'équivalent de {ref} serait {dt} Gy par séance.",
        "col_ref_eqd2": "EQD2 avec {} (Gy)", "col_equiv_dose": "dose équivalente, {} séances",
        "chart_maximum": "Dose équivalente par séance en {} séances (Gy)",
        "k_limiting": "organe limitant", "k_tumour_equiv": "équivalent tumeur (Gy par séance)", "k_sessions": "séances",
        "explain_simulate": "Comment lire : l'EQD2 est la dose qui, donnée en séances de 2 Gy, aurait le même effet biologique ; chaque tissu a la sienne, car les tissus réagissent différemment à la dose par séance. TCP et NTCP sont des probabilités du modèle pour ce scénario fictif.",
        "explain_compare": "Comment lire : une colonne par schéma. Comparez l'EQD2 et le TCP de la tumeur avec l'EQD2 et le NTCP de chaque organe : un schéma n'est meilleur pour un tissu que s'il le domine (TCP plus haut et NTCP plus bas) ; sinon c'est un compromis.",
        "explain_resume": "Comment lire : une colonne par nombre possible de séances restantes ; chaque case donne la dose par séance qui redonne l'EQD2 prévue de ce tissu (LQL-Equiv, pas de 0,01 Gy). La dernière ligne est la dose maximale qui garde chaque organe dans son EQD2 prévue. Simulation : le praticien décide dans le contexte clinique.",
        "explain_maximum": "Comment lire : pour chaque organe, la dose par séance qui donne la même EQD2 que le schéma de référence ; la plus petite est la dose maximale qui ne dépasse aucun organe. Simulation : le praticien décide dans le contexte clinique.",
        "answer_tls": "Réponse : ce tunnel consommerait environ **{ann} MWh par an**, avec une pointe de **{peak} kW** vers {hour} h ; la ventilation représente {ve} % de l'énergie, l'éclairage {li} % et les auxiliaires {au} %{extra}.",
        "tls_extrapolated": " (extrapolé depuis {} jours simulés)",
        "answer_lql": "Réponse : {phys} Gy physiques correspondent à une EQD2 de **{eqt} Gy pour la tumeur** (TCP {tcp} %) et **{eqo} Gy pour {organ}** (NTCP {ntcp} %).",
        "new_case": "Plusieurs valeurs que vous aviez données ont été remplacées. S'il s'agit d'un nouveau cas, cliquez sur **Nouvelle conversation** pour repartir de zéro.",
        "blocked": "Reste en suspens : **{}** (votre dernière demande n'a pas pu être appliquée). Donnez la valeur "
                   "voulue, ou dites **garder** pour conserver la valeur actuelle ; rien n'est calculé avant.",
        "kept": "Entendu : {} garde sa valeur actuelle.",
        "not_named": " — paramètre non nommé dans votre message : vérifiez",
        "held": "Entendu : rien n'est calculé pour l'instant.",
        "fix": "À corriger : {}.",
        "unused": "Je n'ai pas pu utiliser : {}. Rien n'est calculé tant que ce n'est pas précisé.",
        "unread": "Je n'ai pas pu lire votre message (service de langage occupé ou indisponible). Rien n'a été modifié "
                  "ni calculé ; réessayez, ou répondez **oui** pour confirmer le scénario déjà affiché.",
        "limit": "Dans le navigateur, les simulations sont limitées à {} jours, {} tirages Monte Carlo et environ {:,} "
                 "points de temps : réduisez la période ou le nombre de tirages.",
        "failed_run": "Le code a refusé ce scénario : {}",
        "example_done": "Exemple calculé sans modèle de langage : toutes les valeurs sont données et acceptées (voir Variables).",
        "not_computable": "non calculable",
        "status": ("donné par vous", "accepté", "proposé, à accepter"),
        "period": "Période par défaut dans le navigateur (7 jours, 5 tirages) ; modifiable dans la conversation "
                  "(jusqu'à un an, 10 tirages)",
        "tls_analysis": "Sur {days} jours simulés, la puissance de pointe médiane est {peak:,.0f} kW et la moyenne "
                        "{mean:,.0f} kW (facteur de charge {lf:.2f}) ; le tirage représentatif culmine vers {hour} h. Dans "
                        "ce tirage, l'énergie se répartit entre éclairage {li:.0f} %, ventilation {ve:.0f} % et "
                        "auxiliaires {au:.0f} %. La bande 10–90 % entre tirages Monte Carlo a une largeur moyenne de "
                        "{band:.0f} % de la médiane. ",
        "annual_extrapolated": "Le chiffre annuel ({ann:,.0f} MWh/an) extrapole la période par 365/{days} ; ce n'est "
                               "pas une année complète avec ses saisons.",
        "annual_full": "Le chiffre annuel ({ann:,.0f} MWh/an) vient d'une année simulée avec ses saisons.",
        "lql_analysis": "Une dose physique de {phys} Gy correspond à une EQD2 de {eqt} Gy pour la cible et de {eqo} Gy "
                        "pour l'organe à risque, sur {days} jours. Le modèle donne une probabilité de contrôle tumoral de "
                        "{tcp} % et de complication de {ntcp} %. Ce sont des sorties de modèle pour un scénario fictif, "
                        "avec les paramètres de la bibliothèque du code ; elles ne fondent aucune décision clinique.",
    },
}
LABELS = {  # name: (English, French, unit shown)
    "length_m": ("tunnel length", "longueur du tunnel", "m"), "n_tubes": ("tubes", "tubes", ""),
    "n_lanes_per_tube": ("lanes per tube", "voies par tube", ""), "altitude_m": ("altitude", "altitude", "m"),
    "max_depth_m": ("maximum cover", "couverture maximale", "m"), "gradient_percent": ("gradient", "pente", "%"),
    "tunnel_context": ("setting", "contexte", ""), "lighting_type": ("lighting", "éclairage", ""),
    "ventilation_type": ("ventilation", "ventilation", ""),
    "aux_kw_per_km_tube": ("auxiliary load", "charge des auxiliaires", "kW/(km·tube)"),
    "base_fixed_kw": ("fixed load", "charge fixe", "kW"), "traffic_level": ("traffic level", "niveau de trafic", "× reference"),
    "morning_peak_hour": ("morning peak", "pointe du matin", "h"), "evening_peak_hour": ("evening peak", "pointe du soir", "h"),
    "peak_width_h": ("peak width", "largeur des pointes", "h"),
    "traffic_sensitivity": ("traffic sensitivity", "sensibilité au trafic", ""),
    "noise_sigma": ("random variability", "variabilité aléatoire", ""),
    "pollution_probability_per_day": ("pollution events per day", "épisodes de pollution par jour", ""),
    "accident_probability_per_day": ("accidents per day", "accidents par jour", ""),
    "pollution_sensitivity": ("pollution sensitivity", "sensibilité à la pollution", ""),
    "accident_sensitivity": ("accident sensitivity", "sensibilité aux accidents", ""),
    "start_date": ("start date", "date de début", ""), "n_days": ("simulated period", "période simulée", "days"),
    "freq_minutes": ("time step", "pas de temps", "min"), "n_runs": ("Monte Carlo runs", "tirages Monte Carlo", ""),
    "base_seed": ("random seed", "graine aléatoire", ""),
    "organ": ("organ at risk", "organe à risque", ""), "tumour_site": ("tumour site", "site tumoral", ""),
    "dose_per_fraction": ("dose per session", "dose par séance", "Gy"), "n_fractions": ("number of sessions", "nombre de séances", ""),
    "gap_days": ("treatment gap", "interruption", "days"), "reference_dose": ("reference dose", "dose de référence", "Gy"),
    "bifractionated": ("two sessions a day", "deux séances par jour", ""), "scenario_scope": ("scope", "cadre", ""),
    "schedule": ("schedule", "schéma", ""),
}
SHORT = {  # short words that name a field in a partial consent ("yes, only the length"); full labels also count
    "length_m": ("length", "longueur"), "traffic_level": ("traffic", "trafic"), "n_tubes": ("tube",),
    "n_lanes_per_tube": ("lanes", "voies"), "gradient_percent": ("slope", "pente"),
    "n_days": ("period", "duration", "période", "durée"), "n_runs": ("runs", "tirages"),
    "freq_minutes": ("step", "pas"), "dose_per_fraction": ("dose",), "n_fractions": ("sessions", "séances"),
    "tumour_site": ("tumour", "tumor", "tumeur", "cancer"), "organ": ("organ", "organe"),
    "gap_days": ("gap", "interruption", "break", "arrêt"), "reference_dose": ("reference", "référence"),
}
UNIT_FR = {"days": "jours", "× reference": "× référence"}
SOURCES = {"en": {"provided": "your words: “{}”", "convention": "declared convention of the code for “{}”",
                  "default": "declared default of the code", "read": "read by the language model, to confirm"},
           "fr": {"provided": "vos mots : « {} »", "convention": "convention déclarée du code pour « {} »",
                  "default": "valeur par défaut du code", "read": "lu par le modèle de langage, à confirmer"}}
ERRORS = {"en": {"path": "{}: several courses or nested fields are not available here",
                 "unknown": "{}: not a parameter of this code", "number": "{}: the number does not match your words",
                 "level": "{}: no declared convention for these words", "default": "{}: no declared default",
                 "value": "{}: value not usable", "twice": "{}: two different readings in one message",
                 "relative": "{}: your words give a change that I cannot check exactly; please give the final value"},
          "fr": {"path": "{} : plusieurs cures ou champs imbriqués ne sont pas disponibles ici",
                 "unknown": "{} : pas un paramètre de ce code", "number": "{} : le nombre ne correspond pas à vos mots",
                 "level": "{} : pas de convention déclarée pour ces mots", "default": "{} : pas de valeur par défaut déclarée",
                 "value": "{} : valeur inutilisable", "twice": "{} : deux lectures différentes dans le même message",
                 "relative": "{} : vos mots donnent une variation que je ne peux pas vérifier exactement ; indiquez la "
                             "valeur finale"}}

# ---------------------------------------------------------------- formatting


def localise(text, lang):
    if lang != "fr":
        return text
    return re.sub(r"\d[\d,]*\.?\d*", lambda m: m.group(0).replace(",", NBSP).replace(".", ","), text)


def label(name, lang):
    en, fr, _ = LABELS.get(name, (name, name, ""))
    return fr if lang == "fr" else en


def shown(name, value, lang):
    unit = LABELS.get(name, ("", "", ""))[2]
    unit = UNIT_FR.get(unit, unit) if lang == "fr" else unit
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    text = f"{value:,}" if isinstance(value, (int, float)) and not isinstance(value, bool) else str(value)
    return localise(f"{text} {unit}".strip(), lang)


def num(value, fmt, lang):
    """Formatted native number, or 'not computable' when the code returned none."""
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        return T[lang]["not_computable"]
    return localise(format(value, fmt), lang)

# ---------------------------------------------------------------- scenario state


def fresh(model, lang="en"):
    desc = DESC[model]
    state = {"request": "", "task": SINGLE_TASK[model], "inputs": {}, "experiment": {}}
    for group in ("inputs", "experiment"):
        for name, spec in (desc.get(group) or {}).items():
            if spec.get("operational_default") and "default" in spec:
                state[group][name] = dict(value=spec["default"], unit=spec.get("unit"), origin="default",
                                          evidence=None, source=spec.get("operational_default_source"), accepted=True)
    if model == "tls":
        for name, value in (("n_days", 7), ("n_runs", 5)):
            state["experiment"][name] = dict(value=value, unit=desc["experiment"][name].get("unit"), origin="default",
                                             evidence=None, source=T[lang]["period"], accepted=False, kind="default")
    return state


def group_of(model, name):
    desc = DESC[model]
    return "experiment" if name in (desc.get("experiment") or {}) else "inputs" if name in desc["inputs"] else None


def to_scenario(state):
    groups = {g: {n: Parameter(**{k: r.get(k) for k in ("value", "unit", "origin", "evidence", "source")},
                               accepted=bool(r.get("accepted")), conflicts=tuple(r.get("conflicts") or ()))
                  for n, r in (state.get(g) or {}).items()} for g in ("inputs", "experiment")}
    return Scenario(state.get("request", ""), state.get("task", ""), groups["inputs"], groups["experiment"])


def check(model, state, lang="en"):
    res = validate(to_scenario(state), DESC[model])
    return {"decision": res.decision, "issues": [{"parameter": i.field, "code": i.code,
                                                   "message": T[lang]["explain"].get(i.code, i.message)}
                                                  for i in res.issues]}


def propose_defaults(model, state):
    for group in ("inputs", "experiment"):
        for name, spec in (DESC[model].get(group) or {}).items():
            if name not in state[group] and spec.get("default") is not None:
                state[group][name] = dict(value=spec["default"], unit=spec.get("unit"), origin="default", evidence=None,
                                          source="Declared default of the code, proposed", accepted=False, kind="default")


def fold(text):
    return "".join(c for c in unicodedata.normalize("NFD", str(text).lower()) if not unicodedata.combining(c))


ENGLISH_WORDS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
                 "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "fifteen": 15, "twenty": 20, "thirty": 30,
                 "single": 1, "double": 2}


def evidence_numbers(evidence, days=True):
    """Numbers explicitly present in the quoted words (digits, French and English number words); weeks and years
    are converted to days only for a day-valued parameter."""
    text = fold(evidence)
    found = {float(x.replace(",", ".")) for x in re.findall(r"\d+(?:[.,]\d+)?", text.replace(NBSP, ""))}
    for word, value in {**NUMBER_WORDS, **ENGLISH_WORDS}.items():
        if re.search(r"(?<!\w)" + re.escape(word) + r"(?!\w)", text):
            found.add(float(value))
    if re.search(r"\b(sans|aucune?|without|no|none)\b", text):  # "sans interruption", "no gap": zero
        found.add(0.0)
    base = set(found)  # exact calendar conversions: 1 week = 7 days, 1 year = 365 days (no months: not exact)
    if days and re.search(r"\b(semaines?|weeks?)\b", text):
        found |= {7 * x for x in base} | ({7.0} if not base else set())
    if days and re.search(r"\b(annees?|years?|ans)\b|\b(un|1) an\b", text):
        found |= {365 * x for x in base} | ({365.0} if not base else set())
    return found


def exact(evidence, message):
    """The visitor's own characters for a quote found case and accents aside (None if absent)."""
    if not evidence:
        return None
    folded, index = [], []
    for i, c in enumerate(message):
        f = fold(c)
        folded.append(f)
        index.extend([i] * len(f))
    target = fold(evidence)
    at = "".join(folded).find(target)
    return None if at < 0 or not target else message[index[at]:index[at + len(target) - 1] + 1]


def convention_record(spec, evidence, declared):
    value, source = declared
    return dict(value=value, unit=spec.get("unit"), origin="assumption", evidence=None, accepted=False,
                said=evidence, kind="convention", source=source)


def said(evidence, message):
    """The quote is in the visitor's message (case and accents aside): the model never supplies its own words."""
    return bool(evidence) and fold(evidence) in fold(message)


def same(a, b):
    try:
        return a is not None and b is not None and float(a) == float(b)
    except (TypeError, ValueError):
        return str(a) == str(b)


def in_words(value, evidence):
    try:
        return float(value) in evidence_numbers(evidence)
    except (TypeError, ValueError):
        return fold(value) in fold(evidence)


UNIT_WORDS = {"unit:GRAY": r"gy", "unit:M": r"k?m|metres?|meters?", "unit:DAY": r"j|jours?|days?|semaines?|weeks?",
              "unit:PERCENT": r"%|pour ?cent|percent", "unit:KiloW": r"kw", "unit:HR": r"h|heures?|hours?"}


def stated_unit(evidence, spec):
    """The quote contains one of the parameter's declared unit names after a number ("3 Gy", "10 jours")."""
    names = [str(a) for a in spec.get("unit_aliases") or [] if a and not str(a).isdigit()]
    words = "|".join(re.escape(fold(n)) for n in names) or UNIT_WORDS.get(spec.get("unit"), "")
    return bool(words) and bool(re.search(r"\d\s*(?:" + words + r")(?!\w)", fold(evidence)))


def resolve_words(evidence, spec):
    """The descriptor's resolver; for a quote that also holds numbers of other parameters ("conventional fractionation
    in 30 sessions"), it reads the qualitative words alone, unless a number is stated for this very parameter."""
    declared = resolve(evidence, spec)
    if declared is not None or not re.search(r"\d", evidence):
        return declared
    units = UNIT_WORDS.get(spec.get("unit"))
    if units and re.search(r"\d+(?:[.,]\d+)?\s*(?:" + units + r")(?!\w)", fold(evidence)):
        return None  # a number stated for this parameter is never replaced by a convention
    return resolve(re.sub(r"\d+(?:[.,]\d+)?", " ", evidence), spec)


UP = re.compile(r"\b(plus|augmente\w*|ajoute\w*|supplementaires?|more|increase\w*|higher|add|added|extra)\b|\+")
DOWN = re.compile(r"\b(moins|reduit\w*|reduire|baisse\w*|diminue\w*|less|decrease\w*|lower|reduce\w*|fewer)\b")
RELATIVE = re.compile(UP.pattern + "|" + DOWN.pattern)


def relative_change(old, value, evidence):
    """A change stated relative to the current value ('200 m de plus'): exact only if value = current ± a stated number."""
    try:
        before, after = float(old["value"]), float(value)
    except (TypeError, ValueError, KeyError):
        return None
    text = fold(evidence)
    for x in sorted(evidence_numbers(evidence)):
        if UP.search(text) and math.isclose(after, before + x):
            return before, "+", x
        if DOWN.search(text) and math.isclose(after, before - x):
            return before, "−", x
    return None


def apply_value(model, state, v, message, lang):
    """One translated value, checked locally. Returns an error text when it cannot be used (nothing changes then)."""
    e = ERRORS[lang]
    raw_name = str(v.get("field") or "")
    if not NAME.match(raw_name):
        return e["path"].format(raw_name)
    group = group_of(model, raw_name)
    if group is None:
        return e["unknown"].format(raw_name)
    name, spec = raw_name, DESC[model][group][raw_name]
    origin, evidence, raw, unit = v.get("origin"), str(v.get("evidence") or ""), v.get("value"), v.get("unit")
    evidence = exact(evidence, message) or evidence  # the visitor's own characters, as the validator checks them
    old = state[group].get(name)
    quoted = said(evidence, message)
    if old and same(raw, old.get("value")) and not (quoted and in_words(raw, evidence)):
        return None  # the current value repeated without being stated in the message: no change
    if old and (old.get("origin") == "provided" or old.get("accepted")) and not quoted:
        return None  # a later message that does not state this value never overrides it
    try:
        if origin == "convention" and spec.get("type") in ("int", "float") and raw is not None \
                and resolve_words(evidence, spec) is None and float(raw) in evidence_numbers(evidence):
            origin = "provided"  # a number stated in the words is a stated value, whatever the model called it
        if origin == "convention":
            if not said(evidence, message):
                return e["level"].format(label(name, lang))
            declared = resolve_words(evidence, spec)  # only the descriptor's declared expressions give a value;
            if declared is None:                      # other words have no numerical meaning (contract, rule 3)
                return e["level"].format(label(name, lang))
            rec = convention_record(spec, evidence, declared)
        elif origin == "default":
            if spec.get("default") is None:
                return e["default"].format(label(name, lang))
            rec = dict(value=spec["default"], unit=spec.get("unit"), origin="default", evidence=None, accepted=False,
                       kind="default", source="Declared default of the code, proposed")
        elif origin == "provided" and spec.get("unit") == "unit:DAY" and said(evidence, message) \
                and MONTHS.search(fold(evidence)):
            # months have no exact number of days: a declared conversion (n × 365/12, rounded), shown and to accept
            m = MONTHS.search(fold(evidence))
            n = as_int(m.group(1))
            days = round(n * 365 / 12)
            rec = dict(value=int(days) if spec.get("type") == "int" else float(days), unit=spec.get("unit"),
                       origin="assumption", evidence=None, accepted=False, said=evidence, kind="convention",
                       source=f"Declared conversion: {n} month(s) = {n} × 365/12 = {days} days (rounded); to accept.")
        elif origin == "provided":
            numeric = spec.get("type") in ("int", "float")
            stated = evidence_numbers(evidence, days=spec.get("unit") == "unit:DAY") if numeric else set()
            try:
                value, source = parse_number(raw, spec["type"]) if numeric else (raw, None)
            except (ValueError, TypeError):  # e.g. the model returned the word "long": the quote may still be declared
                value, source = None, None
            declared = (resolve_words(evidence, spec) if numeric and (value is None or float(value) not in stated)
                        else None)
            if declared is not None:  # the quote is a declared expression: the descriptor, not the model, gives it
                rec = convention_record(spec, evidence, declared)
            elif value is None:
                return e["value"].format(label(name, lang))
            else:
                change = None
                if numeric and not spec.get("evidence_conversion"):  # with a declared conversion, normalize() reads
                    if not stated or float(value) not in stated:      # the number and unit from the quote itself
                        change = relative_change(old, value, evidence) if old else None
                        if change is None:
                            return e["relative" if RELATIVE.search(fold(evidence)) else "number"].format(label(name, lang))
                if not unit and spec.get("unit") and stated_unit(evidence, spec):
                    unit = spec["unit"]  # the model left out a unit that the visitor's words state ("3 Gy")
                value, unit, conv = normalize(value, unit, evidence, spec)
                if not said(evidence, message):
                    return e["value"].format(label(name, lang))
                source = "; ".join(s for s in (source, conv) if s) or None
                rec = dict(value=value, unit=unit, origin="provided", evidence=evidence, source=source, accepted=False)
                if change:  # exact arithmetic on a stated number, shown to the visitor
                    before, sign, x = change
                    rec["relative"] = f"{shown(name, before, lang)} {sign} {shown(name, x, lang)}"
                    rec["source"] = f"Exact change stated relative to the current value: {rec['relative']}"
        else:
            return e["value"].format(label(name, lang))
    except (ValueError, TypeError):
        return e["value"].format(label(name, lang))
    state[group][name] = rec
    return None

# ---------------------------------------------------------------- what the message asks (deterministic guards)


PURE = re.compile(r"^\s*(oui|yes|ok|okay|d'accord|d’accord|daccord|j'accepte|j’accepte|j'accepte tout|j’accepte tout|"
                  r"i accept|i accept all|accept all|accept everything|tout accepter|accepte tout|vas-y|go|go ahead|"
                  r"valide|je valide|c'est bon|c’est bon|parfait|sure|fine|calcule|calcule-le|lance le calcul|lance|"
                  r"compute|run|run it|recalcule|recompute)(\s*[,;]?\s*(calcule|lance le calcul|compute|run it|go|vas-y))?"
                  r"\s*[.!]*\s*$", re.IGNORECASE)
HOLD = re.compile(r"\b(attends|attendez|wait|hold on|pas encore|not yet|ne calcule pas|don't compute|do not compute|"
                  r"sans calculer|without computing|stop)\b", re.IGNORECASE)
ONLY = re.compile(r"\b(seulement|uniquement|only|just|sauf|except|mais|but)\b", re.IGNORECASE)
ACCEPT_WORD = re.compile(r"\b(oui|yes|ok|okay|d'accord|d’accord|accepte|j'accepte|j’accepte|accept|agree|valide)\b",
                         re.IGNORECASE)
KEEP = re.compile(r"\b(garde|garder|gardez|conserve|conserver|laisse|laisser|annule|annuler|keep|leave|cancel)\b",
                  re.IGNORECASE)


def refusal(model, lang, state=None):
    """Refusal text; during a case, it says the case is unchanged and how to go on (the message may be a remark)."""
    ongoing = state and any(r.get("origin") == "provided" for g in ("inputs", "experiment") for r in state[g].values())
    return T[lang]["refused"] + " " + (T[lang]["refused_ongoing"] if ongoing else T[lang]["refused_hint"][model])


def names(fields, lang):
    return ", ".join(label(f, lang) for f in fields)


def is_pure_confirmation(message):
    return bool(PURE.match(message))


def named_fields(model, state, message):
    text = fold(message)
    out = []
    for group in ("inputs", "experiment"):
        for name in state[group]:
            en, fr, _ = LABELS.get(name, (name, name, ""))
            words = (name, en, fr) + SHORT.get(name, ())
            if any(re.search(r"(?<!\w)" + re.escape(fold(x)) + r"(?!\w)", text) for x in words):
                out.append((group, name))
    return out


def pending(state):
    return [(g, n) for g in ("inputs", "experiment") for n, r in state[g].items()
            if r.get("origin") in ("assumption", "default") and not r.get("accepted")
            and r.get("source") and r.get("value") is not None]


def over_limit(model, state):
    if model != "tls":
        return False
    exp = state["experiment"]
    days = exp.get("n_days", {}).get("value") or 0
    runs = exp.get("n_runs", {}).get("value") or 0
    step = exp.get("freq_minutes", {}).get("value") or 15
    points = days * 1440 / max(step, 1) * runs
    return days > MAX_DAYS or runs > MAX_RUNS or points > MAX_POINTS

# ---------------------------------------------------------------- results (native values only)


def qualification(target, model):
    m = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
    sw = m.get("software", {})
    q = {"software": {k: sw.get(k) for k in ("name", "version", "repository", "commit", "doi", "licence")},
         "nature": m.get("nature"), "uncertainty": m.get("uncertainty") or {},
         "validity_notes": m.get("validity_notes") or [], "note": m.get("note"),
         "verification": (m.get("source_verification") or {}).get("method"),
         "options": {k: str(v) for k, v in (m.get("backend_options") or {}).items()}}
    if model == "lql":
        row = pd.read_csv(target / "indicators.csv").iloc[0].to_dict()
        q["flags"] = {k: bool(row[k]) for k in ("oar_total_valid", "tumour_total_valid", "oar_saturated",
                                                "tumour_saturated") if k in row}
    return q


def files_of(target, names):
    return {n: (target / n).read_text(encoding="utf-8") for n in names if (target / n).exists()}


def tls_results(target, state, lang):
    env = pd.read_csv(target / "envelope.csv")
    rep = pd.read_csv(target / "representative.csv", parse_dates=["timestamp"])
    k = pd.read_csv(target / "kpis.csv").median(numeric_only=True)
    cols = ("lighting_kw", "ventilation_kw", "auxiliary_kw")
    hourly = rep.groupby(rep.timestamp.dt.hour)[list(cols)].mean()
    shares = [float(rep[c].sum()) for c in cols]
    total = sum(shares) or float("nan")
    band = ((env.p90 - env.p10) / env["median"].where(env["median"] != 0)).mean() * 100
    days = state["experiment"].get("n_days", {}).get("value")
    annual = T[lang]["annual_full" if days and days >= 365 else "annual_extrapolated"]
    analysis = localise((T[lang]["tls_analysis"] + annual).format(
        days=days, peak=k.peak_kw, mean=k.mean_kw, lf=k.load_factor, hour=int(hourly.sum(axis=1).idxmax()),
        li=100 * shares[0] / total, ve=100 * shares[1] / total, au=100 * shares[2] / total, band=float(band),
        ann=k.annualized_mwh), lang)
    kpis = [num(k.annualized_mwh, ",.0f", lang), num(k.peak_kw, ",.0f", lang), num(k.load_factor, ".2f", lang),
            num(k.specific_kwh_m_year, ",.0f", lang)]
    extra = "" if days and days >= 365 else T[lang]["tls_extrapolated"].format(days)
    headline = localise(T[lang]["answer_tls"].format(
        ann=f"{k.annualized_mwh:,.0f}", peak=f"{k.peak_kw:,.0f}", hour=int(hourly.sum(axis=1).idxmax()),
        ve=f"{100 * shares[1] / total:.0f}", li=f"{100 * shares[0] / total:.0f}", au=f"{100 * shares[2] / total:.0f}",
        extra=extra), lang)
    return {"kind": "tls", "headline": headline, "kpis": kpis, "analysis": analysis, "qualification": qualification(target, "tls"),
            "series": {"t": env.timestamp.tolist(), "median": env["median"].round(2).tolist(),
                       "p10": env.p10.round(2).tolist(), "p90": env.p90.round(2).tolist()},
            "hourly": {"hour": hourly.index.tolist(), **{c: hourly[c].round(2).tolist() for c in cols}},
            "files": files_of(target, ("representative.csv", "envelope.csv", "daily.csv", "kpis.csv", "manifest.json",
                                       "semantics.ttl"))}


def lql_results(target, ind, lang, organ=""):
    get = lambda k: ind.get(k) if isinstance(ind.get(k), (int, float)) else None  # noqa: E731
    phys, eqt, eqo = get("physical_dose_gy"), get("eqd_tumour_total"), get("eqd_oar_total")
    tcp, ntcp = get("tcp_percent"), get("ntcp_percent")
    headline = T[lang]["answer_lql"].format(
        phys=num(phys, ".1f", lang), eqt=num(eqt, ".1f", lang), eqo=num(eqo, ".1f", lang), organ=organ,
        tcp=num(tcp, ".0f", lang), ntcp=num(ntcp, ".0f", lang))
    analysis = T[lang]["explain_simulate"]
    kpis = [num(eqt, ".1f", lang), num(eqo, ".1f", lang), num(get("bed_tumour"), ".1f", lang),
            f"{num(ntcp, '.0f', lang)} / {num(tcp, '.0f', lang)}"]
    return {"kind": "lql", "headline": headline, "kpis": kpis, "analysis": analysis, "qualification": qualification(target, "lql"),
            "bars": [phys, eqt, eqo], "probs": [tcp, ntcp],
            "files": files_of(target, ("indicators.csv", "manifest.json", "semantics.ttl"))}


def run(model, state, lang):
    out_root = Path(tempfile.mkdtemp(prefix="ws-"))
    try:
        target, ind = execute(to_scenario(state), DESC[model], WS, out_root)
        target = Path(target)
        return tls_results(target, state, lang) if model == "tls" else lql_results(target, ind, lang, state["inputs"]["organ"]["value"])
    finally:
        shutil.rmtree(out_root, ignore_errors=True)


def source_text(rec, lang):
    s = SOURCES[lang]
    if rec.get("origin") == "provided" and rec.get("evidence"):
        return s["provided"].format(rec["evidence"])
    kind = rec.get("kind")
    if kind == "convention":
        return s["convention"].format(rec.get("said", ""))
    if kind in ("default", "read"):
        return s[kind]
    return rec.get("source") or ""


def variables(state, lang):
    stated, accepted, proposed = T[lang]["status"]
    rows = []
    for group in ("inputs", "experiment"):
        for name, rec in state[group].items():
            status = stated if rec.get("origin") == "provided" else accepted if rec.get("accepted") else proposed
            value = ", ".join(organs_of(state)) if name == "organ" and len(organs_of(state)) > 1 else rec.get("value")
            rows.append([label(name, lang), shown(name, value, lang), "", status, source_text(rec, lang)])
    return rows


def clarify_text(model, state, verdict, lang):
    t = T[lang]
    short = lambda i: i["parameter"].split(".")[-1]  # noqa: E731
    waiting = [short(i) for i in verdict["issues"] if i["code"] == "unaccepted_assumption"]
    missing = [short(i) for i in verdict["issues"] if i["code"] == "missing"]
    other = [f"{label(short(i), lang)} ({i['message']})" for i in verdict["issues"]
             if i["code"] not in ("unaccepted_assumption", "missing")]
    rec_of = lambda n: state[group_of(model, n)][n]  # noqa: E731
    conv = [n for n in waiting if rec_of(n).get("kind") == "convention"]
    q = ("« ", " »") if lang == "fr" else ("“", "”")
    sep = " : " if lang == "fr" else ": "
    parts = []
    if missing:
        parts.append(t["needed"].format(", ".join(label(n, lang) for n in missing)))
    if conv:
        parts.append(t["conventions"].format("; ".join(
            f"**{label(n, lang)}{sep}{shown(n, rec_of(n)['value'], lang)}** ({q[0]}{rec_of(n).get('said', '')}{q[1]})"
            for n in conv)))
    if len(waiting) > len(conv):
        parts.append(t["defaults"].format(len(waiting) - len(conv)))
    if waiting:
        parts.append(t["pending"])
    if other:
        parts.append(t["fix"].format("; ".join(other)))
    return "\n\n".join(parts)

# ---------------------------------------------------------------- LQL: several organs and schedules, resumption, maximum dose
# Only LQL-Equiv computes (lql_workbench, lql_interruption). Here, deterministic reading of the visitor's words:
# schedules ("20 × 3 Gy", "39 sessions of 2 Gy with a 10-day break"), sessions already given and still possible,
# "maximum dose", "all organs at risk". Groups of organs come from the ontology; the library's own lists decide
# whether a name is an organ or a tumour site. Anything ambiguous is asked.

try:
    _LIBRARY = _backend(WS, DESC["lql"]).load_library()
    LIB_ORGANS, LIB_SITES = list(_LIBRARY.organ_names), list(_LIBRARY.tumour_names)
except Exception:  # noqa: BLE001 - the names only refine readings; every run is checked again by the library
    LIB_ORGANS, LIB_SITES = [], []
try:
    GROUPS, NAMES = wb.anatomy(WS), wb.names(WS)
except Exception:  # noqa: BLE001 - without the ontology, groups and names are simply not offered
    GROUPS, NAMES = {}, {"organ": {}, "tumour_site": {}}


def names_in(message):
    """Organs and tumour sites named in the words, from the ontology's labels (longest label wins; a label shared by
    an organ and a site is ambiguous and left to the reading model)."""
    text, found = fold(message), []
    for kind, table in NAMES.items():
        for name, alts in table.items():
            for label in [name] + alts:
                for m in re.finditer(r"(?<!\w)" + re.escape(fold(label)) + r"(?!\w)", text):
                    found.append((m.start(), m.end(), kind, name))
    found = [f for f in found if not any(o[0] <= f[0] and o[1] >= f[1] and o[1] - o[0] > f[1] - f[0] for o in found)]
    spans = {}
    for start, end, kind, name in found:
        spans.setdefault((start, end), set()).add((kind, name))
    out = {"organ": [], "tumour_site": []}
    for (start, end), hits in sorted(spans.items()):
        if len(hits) == 1:
            kind, name = next(iter(hits))
            if name not in [n for n, _ in out[kind]]:
                out[kind].append((name, exact(message[start:end], message) or message[start:end]))
    return out

_WORDS = {**{fold(k): v for k, v in NUMBER_WORDS.items()}, **ENGLISH_WORDS}
NUM = r"(\d+|" + "|".join(re.escape(w) for w in sorted(_WORDS, key=len, reverse=True)) + r")"
SESS = r"(?:seances?|sessions?|fractions?)"
SCHED = re.compile(r"(\d+)\s*(?:x|×|\*)\s*(\d+(?:[.,]\d+)?)(?:\s*gy)?\b|" + NUM + r"\s*" + SESS
                   + r"\s*(?:de|of|a|at)\s*(\d+(?:[.,]\d+)?)\s*gy\b")
GAP = re.compile(r"(?:interruption|arret|pause|gap|break|coupure)\s*(?:de|of)?\s*" + NUM + r"\s*(jours?|days?|semaines?|weeks?)"
                 r"|" + NUM + r"[- ]?(jours?|days?|semaines?|weeks?)\s*(?:d'?\s*)?(?:de\s*)?(?:gap|break|interruption|pause|arret)")
INTERRUPT = re.compile(r"\b(arret\w*|interruption|interrompu\w*|pause|break|gap|stopped|interrupted|vacances|holidays?)\b")
RESUMING = re.compile(r"\b(rattrap\w*|compens\w*|reprise|reprendre|restantes?|restent|reste(?:ra|rait)?|meme nombre|"
                      r"remain\w*|left|catch up|resum\w*|same number|still possible)\b")
MAXIMUM = re.compile(r"\b(dose max\w*|max\w* dose|dose la plus (?:haute|elevee)|highest dose|plus haute dose)\b")
MINIMUM = re.compile(r"\b(dose min\w*|min\w* dose|minimi\w*|epargn\w*|spar\w*|lowest dose|dose la plus (?:basse|faible))\b")
ALL_OARS = re.compile(r"\b(tous les organes|tous les oar|all (?:the )?organs|all oars|chaque organe|every organ)\b")
DONE = [re.compile(NUM + r"\s*" + SESS + r"\s*(?:deja\s*)?(?:faites?|effectuees?|realisees?|delivrees?|done|given|"
                   r"delivered|completed|received)\b"),
        re.compile(r"\b(?:deja|already)\s*" + NUM + r"\s*" + SESS),
        re.compile(r"\b(?:apres|after)\s*" + NUM + r"\s*" + SESS)]
AT_SESSION = re.compile(r"\b(?:a la|at the|at session)\s*" + NUM + r"\s*(?:e|eme|th|st|nd|rd)?\s*(?:seance|session|fraction)\b")
REMAIN = [re.compile(r"(?:reste(?:ra|rait)?|only|seulement|plus que)\s*(?:que\s*)?" + NUM + r"\s*" + SESS),
          re.compile(NUM + r"\s*" + SESS + r"\s*(?:restantes?|remaining|left|possibles?)")]
SAME_NUMBER = re.compile(r"\b(meme nombre|same number|garder le nombre|keep the number|toutes les seances prevues|"
                         r"all (?:the )?planned sessions)\b")
TARGET = re.compile(r"\b(?:en|in|sur|over)\s*" + NUM + r"\s*" + SESS)
BARE = re.compile(r"^\s*" + NUM + r"\s*" + SESS + r"?\s*[.!]?\s*$")
MONTHS = re.compile(NUM + r"\s*(?:mois|months?)\b")
SEQUENCE = re.compile(r"\b(puis|ensuite|suivie?s? de|then|followed by|runs?|cures?|cursus|series|courses?|boost)\b")
COMPARE = re.compile(r"\b(compar\w*|versus|vs|plutot que|rather than|ou bien|either)\b")
FRAGMENT = re.compile(r"\b\d+\s*[a-wyz]\s*\d+(?:[.,]\d+)?(?:\s*gy)?\b")


def as_int(token):
    return int(token) if token.isdigit() else int(_WORDS[token])


def schedules_in(message):
    """Schedules stated in the words, each with the interruption written in its own clause (exact numbers only)."""
    text = fold(message)
    found = list(SCHED.finditer(text))
    out = []
    for i, m in enumerate(found):
        n, d = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
        clause = text[m.end():found[i + 1].start() if i + 1 < len(found) else len(text)]
        out.append({"sessions": as_int(n), "dose": float(d.replace(",", ".")), "gap_days": gap_in(clause) or 0.0,
                    "said": exact(m.group(0), message) or m.group(0), "start": m.start()})
    return out


def gap_in(text):
    m = GAP.search(fold(text))
    if not m:
        return None
    number, unit = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
    return float(as_int(number) * (7 if unit.startswith(("semaine", "week")) else 1))


def gap_quote(message):
    """The visitor's own words for the interruption ("5 jours d'arrêt"), for the provenance."""
    m = GAP.search(fold(message))
    return (exact(m.group(0), message) if m else None) or message


def organs_of(state):
    if state.get("organs"):
        return list(state["organs"])
    organ = state["inputs"].get("organ", {}).get("value")
    return [organ] if organ else []


def schedule_label(s, lang):
    gap = s.get("gap_days") or 0
    text = f"{s['sessions']} × {localise(format(s['dose'], 'g'), lang)} Gy"
    return text + (f", {T[lang]['gap_short'].format(localise(format(gap, 'g'), lang))}" if gap else "")


def sort_tissues(values):
    """A tumour site read as an organ is moved to the tumour site (the library's lists decide); several organs
    at risk are kept: the first goes through the normal checks, the others are returned."""
    has_site = any(v.get("field") == "tumour_site" for v in values)
    organs, rest = [], []
    for v in values:
        if v.get("field") == "organ" and LIB_ORGANS and v.get("value") not in LIB_ORGANS and v.get("value") in LIB_SITES:
            if has_site:
                continue  # a tumour site is already read: this name is not an organ at risk
            v, has_site = dict(v, field="tumour_site"), True
        (organs if v.get("field") == "organ" else rest).append(v)
    return rest + organs[:1], organs[1:]


def lql_reading(state, values, message, lang, errors):
    """Deterministic part of an LQL turn, before the model's values are applied. Returns the values to apply."""
    text = fold(message)
    L = state.setdefault("lql", {"mode": "simulate"})
    awaiting = L.pop("awaiting", None)
    short_answer = awaiting and (BARE.match(text) or re.match(r"^\s*" + NUM + r"\s*(jours?|days?|semaines?|weeks?)?"
                                                                  r"\s*[.!]?\s*$", text))
    if short_answer:  # an answer to the question just asked is read only as that answer, never by the model
        values = []
    scheds = schedules_in(message)
    if MAXIMUM.search(text):
        L["mode"] = "maximum"
    elif MINIMUM.search(text):
        L["mode"] = "minimum"
    elif INTERRUPT.search(text) and RESUMING.search(text):
        L["mode"] = "resume"
    elif len(scheds) >= 2:  # one after the other, or alternatives? asked when the words do not say
        L["mode"] = "compare" if COMPARE.search(text) else "sequence" if SEQUENCE.search(text) else "choose"
    if awaiting == "choose" and L.get("mode") == "choose":
        one_after = SEQUENCE.search(text) or re.search(r"enchain|successi|apres l.autre|one after|in turn", text)
        L["mode"] = "compare" if COMPARE.search(text) else "sequence" if one_after else "choose"
    if scheds:
        L["schedules"] = scheds
    gap = gap_in(message)
    if len(scheds) >= 2:
        L["prefix_gap"] = gap_in(text[:scheds[0]["start"]])
    if L["mode"] == "sequence" and len(L.get("schedules") or []) >= 2:  # the break written between two courses
        listed = L["schedules"]                                          # comes before the next course
        courses = [dict(sc, gap_days=0.0) for sc in listed]
        for i in range(len(listed) - 1):
            courses[i + 1]["gap_days"] = listed[i]["gap_days"]
        if L.get("prefix_gap") and len(courses) == 2 and not courses[1]["gap_days"]:
            courses[1]["gap_days"] = L["prefix_gap"]
        L["courses"] = courses
    fragments = [f for f in FRAGMENT.findall(text) if not SCHED.fullmatch(f)]
    unresolved = set(state.get("unresolved") or [])
    if fragments:  # "20c3.5": a schedule written in a way that is not recognised; never guessed
        L["unparsed"] = exact(fragments[0], message) or fragments[0]
        unresolved.add("schedule")
    elif not short_answer:
        L.pop("unparsed", None)
        unresolved.discard("schedule")
    state["unresolved"] = sorted(unresolved)
    if L["mode"] in ("compare", "resume", "maximum", "minimum", "sequence", "choose") and scheds:  # the parser, not the model, reads the schedules
        values = [v for v in values if v.get("field") not in ("dose_per_fraction", "n_fractions", "gap_days")]
        first = scheds[0]
        for name, value in (("dose_per_fraction", first["dose"]), ("n_fractions", first["sessions"])):
            state["inputs"][name] = dict(value=value, unit="unit:GRAY" if name == "dose_per_fraction" else "unit:NUM",
                                         origin="provided", evidence=first["said"], source="schedule read in your words",
                                         accepted=False)
        g = gap if L["mode"] == "resume" else (first["gap_days"] or None)
        if g is not None:  # only an interruption written in the words; otherwise the declared default is proposed
            state["inputs"]["gap_days"] = dict(value=float(g), unit="unit:DAY", origin="provided", evidence=gap_quote(message),
                                               accepted=False, source="interruption read in your words")
    if L["mode"] == "resume":
        for rx in DONE:
            m = rx.search(text)
            if m:
                L["done"], _ = as_int(m.group(1)), L.pop("ambiguous_done", None)
                break
        else:
            m = AT_SESSION.search(text)
            if m and "done" not in L:
                L["ambiguous_done"] = as_int(m.group(1))
        if SAME_NUMBER.search(text):
            L["same_number"] = True
        for rx in REMAIN:
            m = rx.search(text)
            if m:
                L["remaining"] = as_int(m.group(1))
                break
    if L["mode"] == "maximum":
        m = TARGET.search(text)
        if m:
            L["target"] = as_int(m.group(1))
    if awaiting == "gap":  # "5", "5 jours", "two weeks": the interruption asked for
        m = re.match(r"^\s*" + NUM + r"\s*(jours?|days?|semaines?|weeks?)?\s*[.!]?\s*$", text)
        if m:
            days = as_int(m.group(1)) * (7 if (m.group(2) or "").startswith(("semaine", "week")) else 1)
            state["inputs"]["gap_days"] = dict(value=float(days), unit="unit:DAY", origin="provided", evidence=message,
                                               accepted=False, source="interruption read in your words")
    bare = BARE.match(text)
    if bare and awaiting and awaiting != "gap":  # a short answer to the question just asked
        number = as_int(bare.group(1))
        if awaiting == "done_ambiguous":
            if number in (L.get("ambiguous_done", 0) - 1, L.get("ambiguous_done")):
                L["done"] = number
                L.pop("ambiguous_done", None)
        else:
            L[awaiting] = number
    if not short_answer:  # what the model missed but the ontology's names show in the words
        seen = names_in(message)
        if not any(v.get("field") == "tumour_site" for v in values) and len(seen["tumour_site"]) == 1:
            name, quote = seen["tumour_site"][0]
            values.append({"field": "tumour_site", "value": name, "origin": "provided", "evidence": quote})
        if not any(v.get("field") == "organ" for v in values):
            values += [{"field": "organ", "value": name, "origin": "provided", "evidence": quote}
                       for name, quote in seen["organ"]]
    values, extra = sort_tissues(values)
    said_extra = []
    for v in extra:
        name = str(v.get("value") or "")
        if (LIB_ORGANS and name not in LIB_ORGANS) or not said(str(v.get("evidence") or ""), message):
            errors.append(ERRORS[lang]["value"].format(label("organ", lang)))
        else:
            said_extra.append(name)
    L["extra_organs"] = said_extra
    return values


def lql_after(state, old, message, lang, parts):
    """After the values are applied: organs list, "all organs" from the ontology, consistency with the tumour site."""
    t, L = T[lang], state["lql"]
    if L.get("unparsed"):
        parts.append(t["unparsed"].format(L["unparsed"]))
    organ_now = state["inputs"].get("organ")
    if organ_now and organ_now != old["inputs"].get("organ") and organ_now.get("kind") != "group":
        state["organs"] = [organ_now["value"]] + [o for o in L.pop("extra_organs", []) if o != organ_now["value"]]
        if len(state["organs"]) > 1:
            parts.append(t["organs_noted"].format(", ".join(state["organs"])))
    site = state["inputs"].get("tumour_site", {}).get("value")
    key = wb.group_of_site(GROUPS, site) if site else None
    if ALL_OARS.search(fold(message)):
        if not key:
            parts.append(t["group_none"])
        else:
            organs = GROUPS[key]["organs"]
            state["organs"] = list(organs)
            state["inputs"]["organ"] = dict(value=organs[0], unit=None, origin="assumption", evidence=None,
                                            accepted=False, kind="group", said=GROUPS[key]["label"],
                                            source=f"Anatomical group '{GROUPS[key]['label']}' of the ontology "
                                                   f"({GROUPS[key]['iri']}): {', '.join(organs)}")
            parts.append(t["group_proposed"].format(GROUPS[key]["label"], ", ".join(organs)))
    elif site and site != old["inputs"].get("tumour_site", {}).get("value") and key and organs_of(state) \
            and state["inputs"].get("organ") == old["inputs"].get("organ"):
        stray = [o for o in organs_of(state) if o not in GROUPS[key]["organs"]]
        if stray:  # an organ of an earlier case does not belong to this tumour site's group: asked again
            state["inputs"].pop("organ", None)
            state["organs"] = []
            parts.append(t["organs_dropped"].format(", ".join(stray), site, GROUPS[key]["label"]))


def lql_missing(state, lang):
    """What the chosen kind of question still needs, with the question to ask (deterministic)."""
    t, L = T[lang], state.get("lql") or {}
    mode = L.get("mode", "simulate")
    planned = state["inputs"].get("n_fractions", {}).get("value")
    if mode == "resume":
        if state["inputs"].get("gap_days", {}).get("origin") != "provided":
            return "gap", t["ask_gap"]
        if L.get("ambiguous_done") and "done" not in L:
            n = L["ambiguous_done"]
            return "done_ambiguous", t["ask_done_ambiguous"].format(n, n - 1, n)
        if "done" not in L:
            return "done", t["ask_done"]
        if L.get("same_number") and planned and "remaining" not in L:
            L["remaining"] = int(planned) - int(L["done"])
        if "remaining" not in L:
            return "remaining", t["ask_remaining"]
        if planned and not 0 <= L["done"] < planned:
            return "done", t["ask_done"]
    if mode == "maximum" and "target" not in L:
        return "target", t["ask_target"]
    if L.get("unparsed"):
        return "unparsed", t["unparsed"].format(L["unparsed"])
    if mode == "choose":
        return "choose", t["ask_choose"]
    return None, None


def lql_plan(state, lang):
    """The calculation about to run, in one line (shown before the visitor's yes)."""
    t, L = T[lang], state.get("lql") or {}
    mode, organs = L.get("mode", "simulate"), ", ".join(organs_of(state))
    inp = {n: r.get("value") for n, r in state["inputs"].items()}
    planned = {"sessions": inp.get("n_fractions"), "dose": inp.get("dose_per_fraction"), "gap_days": 0}
    if mode == "compare":
        return t["plan_compare"].format("; ".join(schedule_label(s, lang) for s in L["schedules"]), organs)
    if mode == "resume":
        return t["plan_resume"].format(schedule_label(planned, lang), L["done"], localise(format(inp.get("gap_days") or 0, "g"), lang),
                                       L["remaining"], organs)
    if mode == "maximum":
        ref = L.get("schedules", [planned])[0]
        return t["plan_maximum"].format(L["target"], schedule_label(ref, lang), organs)
    if mode == "minimum":
        ref = L.get("schedules", [planned])[0]
        return t["plan_minimum"].format(schedule_label(ref, lang), organs)
    if mode == "sequence":
        return t["plan_sequence"].format(course_chain(L["courses"], lang), organs)
    return ""


def course_chain(courses, lang):
    t = T[lang]
    parts = []
    for i, c in enumerate(courses):
        text = f"{c['sessions']} × {localise(format(c['dose'], 'g'), lang)} Gy"
        if i and c.get("gap_days"):
            text = t["after_gap"].format(localise(format(c["gap_days"], "g"), lang)) + " " + text
        parts.append(text)
    return t["then"].join(parts)


def lql_compute(state, lang):
    """Runs the chosen question with LQL-Equiv and builds a clear answer, a table of all cases and a chart."""
    t, L = T[lang], state.get("lql") or {}
    mode, organs = L.get("mode", "simulate"), organs_of(state)
    inp = {n: r.get("value") for n, r in state["inputs"].items()}
    site, ref_dose = inp["tumour_site"], float(inp.get("reference_dose") or 2.0)
    planned = wb.Schedule(float(inp["dose_per_fraction"]), int(inp["n_fractions"]), float(inp.get("gap_days") or 0))
    g = lambda v, f=".1f": num(v, f, lang)  # noqa: E731
    if mode in ("simulate", "compare"):
        scheds = ([planned] if mode == "simulate" else
                  [wb.Schedule(float(s["dose"]), int(s["sessions"]), float(s["gap_days"])) for s in L["schedules"]])
        r = wb.table(WS, DESC["lql"], site, organs, scheds, ref_dose)
        labels = [schedule_label(asdict_s(s), lang) for s in scheds]
        rows = r["rows"]
        by = {(i, o): next(x for x in rows if x["schedule"] == asdict_s(s) and x["organ"] == o)
              for i, s in enumerate(scheds) for o in organs}
        head = [t["col_tissue"]] + labels
        table = [[f"{site} ({t['target']})"] + [f"EQD2 {g(by[(i, organs[0])]['eqd_tumour_total'])} Gy · TCP "
                                                 f"{g(by[(i, organs[0])]['tcp_percent'], '.0f')} %" for i in range(len(scheds))]]
        table += [[o] + [f"EQD2 {g(by[(i, o)]['eqd_oar_total'])} Gy · NTCP {g(by[(i, o)]['ntcp_percent'], '.0f')} %"
                         for i in range(len(scheds))] for o in organs]
        first = by[(0, organs[0])]
        headline = t["answer_table"].format(
            "; ".join(f"{labels[i]} → EQD2 {t['target']} {g(by[(i, organs[0])]['eqd_tumour_total'])} Gy "
                      f"(TCP {g(by[(i, organs[0])]['tcp_percent'], '.0f')} %)" for i in range(len(scheds))),
            "; ".join(f"{o} {g(by[(0, o)]['eqd_oar_total'])} Gy (NTCP {g(by[(0, o)]['ntcp_percent'], '.0f')} %)"
                      for o in organs) if len(scheds) == 1 else t["see_table"])
        chart = {"categories": [t["target"]] + organs, "unit": "Gy", "title": t["chart_eqd2"],
                 "series": [{"name": labels[i], "values": [by[(i, organs[0])]["eqd_tumour_total"]]
                             + [by[(i, o)]["eqd_oar_total"] for o in organs]} for i in range(len(scheds))]}
        kpis = [(g(first["eqd_tumour_total"]), t["k_eqd_target"]), (g(first["tcp_percent"], ".0f"), "TCP (%)"),
                (str(len(organs)), t["k_organs"]), (str(len(scheds)), t["k_schedules"])]
        payload = r
    elif mode == "resume":
        r = wb.resumption(WS, DESC["lql"], site, organs, planned, int(L["done"]), float(inp.get("gap_days") or 0),
                          int(L["remaining"]))
        rows = r["equivalent"]
        last = rows[-1]
        n, d = last["sessions"], last["tumour"]["dose_per_session"]
        unc = r["uncompensated"]
        headline = t["answer_resume"].format(
            n=n, d=g(d, ".2f"), eqd=g(r["planned"]["tumour_eqd2"]), loss=g(abs(unc["tumour_difference_percent"] or 0)),
            dp=g(planned.dose, "g"), m=g(last["maximum_dose"], ".2f"), lim=last["limiting_organ"] or "—")
        head = [t["col_tissue"], t["col_planned_eqd2"]] + [t["col_n_sessions"].format(x["sessions"]) for x in rows]
        table = [[f"{site} ({t['target']})", g(r["planned"]["tumour_eqd2"])] + [f"{g(x['tumour']['dose_per_session'], '.2f')} Gy"
                                                                              for x in rows]]
        table += [[o, g(r["planned"]["organs_eqd2"].get(o))] + [f"{g(x['organs'][o]['equivalent']['dose_per_session'], '.2f')} Gy"
                                                                for x in rows] for o in organs]
        table += [[t["row_max"], ""] + [f"{g(x['maximum_dose'], '.2f')} Gy ({x['limiting_organ'] or '—'})" for x in rows]]
        chart = {"categories": [t["target"]] + organs, "unit": "Gy", "title": t["chart_resume"].format(n),
                 "series": [{"name": t["series_equivalent"],
                             "values": [d] + [last["organs"][o]["equivalent"]["dose_per_session"] for o in organs]}],
                 "line": {"value": last["maximum_dose"], "label": t["line_max"]}, "zoom": True}
        kpis = [(g(d, ".2f"), t["k_dose_resume"].format(n)), (g(last["maximum_dose"], ".2f"), t["k_max_dose"]),
                (g(abs(unc["tumour_difference_percent"] or 0)), t["k_loss"]), (g(r["planned"]["tumour_eqd2"]), t["k_planned_eqd2"])]
        payload = r
    elif mode == "sequence":
        courses = [wb.Schedule(float(c["dose"]), int(c["sessions"]), float(c["gap_days"])) for c in L["courses"]]
        r = wb.sequence(WS, DESC["lql"], site, organs, courses, ref_dose)
        rows = r["rows"]
        first = rows[0]
        chain = course_chain(L["courses"], lang)
        headline = t["answer_sequence"].format(
            chain=chain, eqt=g(first["eqd_tumour_total"]), tcp=g(first["tcp_percent"], ".0f"),
            organs="; ".join(f"{x['organ']} {g(x['eqd_oar_total'])} Gy (NTCP {g(x['ntcp_percent'], '.0f')} %)" for x in rows))
        labels = [t["col_course"].format(i + 1, f"{c['sessions']} × {localise(format(c['dose'], 'g'), lang)} Gy")
                  for i, c in enumerate(L["courses"])]
        head = [t["col_tissue"]] + labels + [t["col_total"]]
        table = [[f"{site} ({t['target']})"] + [g(c["eqd_tumour"]) for c in first["courses"]]
                 + [f"{g(first['eqd_tumour_total'])} Gy · TCP {g(first['tcp_percent'], '.0f')} %"]]
        table += [[x["organ"]] + [g(c["eqd_oar"]) for c in x["courses"]]
                  + [f"{g(x['eqd_oar_total'])} Gy · NTCP {g(x['ntcp_percent'], '.0f')} %"] for x in rows]
        chart = {"categories": [t["target"]] + [x["organ"] for x in rows], "unit": "Gy", "title": t["chart_sequence"],
                 "series": [{"name": labels[i], "values": [first["courses"][i]["eqd_tumour"]]
                             + [x["courses"][i]["eqd_oar"] for x in rows]} for i in range(len(courses))]
                 + [{"name": t["col_total"], "values": [first["eqd_tumour_total"]] + [x["eqd_oar_total"] for x in rows]}]}
        kpis = [(g(first["eqd_tumour_total"]), t["k_eqd_target"]), (g(first["tcp_percent"], ".0f"), "TCP (%)"),
                (str(len(courses)), t["k_courses"]), (g(first["physical_dose_gy"]), t["k_physical"])]
        payload = r
    elif mode == "minimum":
        ref_s = L.get("schedules", [None])[0]
        ref = (wb.Schedule(float(ref_s["dose"]), int(ref_s["sessions"]), float(ref_s["gap_days"])) if ref_s else planned)
        r = wb.minimum_organ_dose(WS, DESC["lql"], site, organs, ref)
        rows = r["rows"]
        pct = lambda v: "—" if v is None else localise(f"{v:+.1f}", lang)  # noqa: E731
        per_organ = ", ".join(f"{o} → {r['per_organ'][o]}" for o in organs)
        headline = t["answer_minimum"].format(ref=schedule_label(asdict_s(ref), lang), n=r["best_sessions"],
                                             d=g(r["best_dose"], ".2f"), w=pct(r["best_worst_percent"]), per=per_organ)
        head = [t["col_tissue"]] + [t["col_n_sessions"].format(x["sessions"]) for x in rows]
        table = [[f"{site} ({t['target']})"] + [f"{g(x['tumour']['dose_per_session'], '.2f')} Gy" for x in rows]]
        table += [[o] + [f"{g(x['organs'][o]['eqd2_with_tumour_schedule'])} Gy ({pct(x['organs'][o]['difference_with_tumour_schedule_percent'])} %)"
                         for x in rows] for o in organs]
        chart = {"categories": [str(x["sessions"]) for x in rows], "unit": "%", "title": t["chart_minimum"],
                 "series": [{"name": o, "values": [x["organs"][o]["difference_with_tumour_schedule_percent"] for x in rows]}
                            for o in organs]}
        kpis = [(str(r["best_sessions"]), t["k_best_sessions"]), (g(r["best_dose"], ".2f"), t["k_best_dose"]),
                (pct(r["best_worst_percent"]), t["k_worst_organ"]), (str(len(rows)), t["k_cases"])]
        payload = r
    else:  # maximum
        ref_s = L.get("schedules", [None])[0]
        ref = (wb.Schedule(float(ref_s["dose"]), int(ref_s["sessions"]), float(ref_s["gap_days"])) if ref_s else planned)
        r = wb.maximum_dose(WS, DESC["lql"], site, organs, ref, int(L["target"]))
        doses = r["organ_equivalent_doses"]
        headline = t["answer_maximum"].format(n=r["sessions"], m=g(r["maximum_dose"], ".2f"), lim=r["limiting_organ"] or "—",
                                             ref=schedule_label(asdict_s(ref), lang), dt=g(r["tumour_equivalent_dose"], ".2f"))
        head = [t["col_tissue"], t["col_ref_eqd2"].format(schedule_label(asdict_s(ref), lang)),
                t["col_equiv_dose"].format(r["sessions"])]
        table = [[f"{site} ({t['target']})", g(r["planned"]["tumour_eqd2"]), f"{g(r['tumour_equivalent_dose'], '.2f')} Gy"]]
        table += [[o, g(r["planned"]["organs_eqd2"].get(o)), f"{g(doses[o], '.2f')} Gy"] for o in organs]
        chart = {"categories": [t["target"]] + organs, "unit": "Gy", "title": t["chart_maximum"].format(r["sessions"]),
                 "series": [{"name": t["series_equivalent"], "values": [r["tumour_equivalent_dose"]] + [doses[o] for o in organs]}],
                 "line": {"value": r["maximum_dose"], "label": t["line_max"]}, "zoom": True}
        kpis = [(g(r["maximum_dose"], ".2f"), t["k_max_dose"]), (r["limiting_organ"] or "—", t["k_limiting"]),
                (g(r["tumour_equivalent_dose"], ".2f"), t["k_tumour_equiv"]), (str(r["sessions"]), t["k_sessions"])]
        payload = r
    software = DESC["lql"]["software"]
    qualification = {"software": {k: software.get(k) for k in ("name", "version", "repository", "commit", "doi", "licence")},
                     "nature": DESC["lql"].get("nature"), "uncertainty": {}, "validity_notes": DESC["lql"].get("validity_notes") or [],
                     "verification": "sha256_lf", "options": payload.get("options") or {}}
    return {"kind": "lql_table", "headline": headline, "kpis": [k for k, _ in kpis], "kpi_labels": [lab for _, lab in kpis],
            "table": {"head": head, "rows": table}, "chart": chart, "analysis": t["explain_" + mode],
            "qualification": qualification,
            "files": {"results.json": json.dumps(payload, ensure_ascii=False, indent=1, default=str)}}


def asdict_s(s):
    return {"dose": s.dose, "sessions": s.sessions, "gap_days": s.gap_days} if isinstance(s, wb.Schedule) else s

# ---------------------------------------------------------------- API used by the page (JSON in, JSON out)


def api_fresh(model, lang):
    return json.dumps(fresh(model, lang))


def api_needs_reading(message):
    """A pure confirmation is handled without the language model."""
    return json.dumps(not is_pure_confirmation(message.strip()))


def api_summary(state_json):
    state = json.loads(state_json)
    summary = {g: {n: {k: r.get(k) for k in ("value", "unit", "origin", "accepted")}
                   for n, r in state[g].items()} for g in ("inputs", "experiment")}
    # context only, so that "that means 1200 m" refers to the parameter left unresolved; values are never taken from it
    summary["unresolved"] = state.get("unresolved") or []
    summary["previous_message"] = ((state.get("request") or "").splitlines() or [""])[-1][:300]
    return json.dumps(summary, ensure_ascii=False)


def respond(model, lang, state, reply, results=None, decision=None):
    verdict = decision or check(model, state, lang)["decision"]
    return json.dumps({"state": state, "reply": reply.strip(), "decision": verdict,
                       "variables": variables(state, lang), "results": results}, ensure_ascii=False, default=str)


def compute(model, lang, state):
    if over_limit(model, state):
        return respond(model, lang, state, T[lang]["limit"].format(MAX_DAYS, MAX_RUNS, MAX_POINTS), decision="clarify")
    try:
        mode = (state.get("lql") or {}).get("mode", "simulate")
        if model == "lql" and (mode != "simulate" or len(organs_of(state)) > 1):
            results = lql_compute(state, lang)  # several organs or schedules, resumption, maximum dose
        else:
            results = run(model, state, lang)
    except ValueError as exc:
        return respond(model, lang, state, T[lang]["failed_run"].format(exc), decision="clarify")
    # the answer, in plain words, comes first in the conversation; the details are on the right
    return respond(model, lang, state, results.get("headline") or T[lang]["computed"], results=results,
                   decision="execute")


def api_turn(model, lang, state_json, message, parsed_json):
    """One turn. parsed_json is the language model's reading ('' when not read or not needed)."""
    t = T[lang]
    state = json.loads(state_json)
    message = message.strip()

    if is_pure_confirmation(message):  # deterministic: accept what was shown, then run if the validator agrees
        if state.get("unresolved"):  # a request that could not be applied is never replaced by the old value
            return respond(model, lang, state, t["blocked"].format(names(state["unresolved"], lang)), decision="clarify")
        for g, n in pending(state):
            state[g][n]["accepted"] = True
        verdict = check(model, state, lang)
        if verdict["decision"] == "execute":
            key, question = lql_missing(state, lang) if model == "lql" else (None, None)
            if key:  # the kind of question asked still needs an answer (sessions given, remaining, ...)
                state["lql"]["awaiting"] = key
                return respond(model, lang, state, question, decision="clarify")
            return compute(model, lang, state)
        return respond(model, lang, state, clarify_text(model, state, verdict, lang))

    if not parsed_json:  # a composite message that could not be read: nothing changes
        return respond(model, lang, state, t["unread"])

    parsed = json.loads(parsed_json)
    state["request"] = (state["request"] + "\n" + message).strip()
    task = str(parsed.get("task") or "")
    if task == "unsupported":
        return respond(model, lang, state, refusal(model, lang, state), decision="refuse")
    allowed = DESC[model]["tasks"]["supported"] if model == "lql" else [SINGLE_TASK[model]]
    if model == "lql" and ("compar" in fold(task) or len(schedules_in(message)) >= 2):
        task = ""  # comparisons are supported here; the schedules are read from the words
    if task and task not in allowed:
        return respond(model, lang, state, t["not_here"], decision="clarify")

    errors = []
    old = json.loads(json.dumps(state))  # to report what this message changed
    values = [v if isinstance(v, dict) else {} for v in parsed.get("values") or []]
    if model == "lql":  # schedules, sessions, groups: read deterministically from the words
        values = lql_reading(state, values, message, lang, errors)
    fields = [str(v.get("field") or "") for v in values]
    twice = {f for f in fields if fields.count(f) > 1}
    errors += [ERRORS[lang]["twice"].format(label(f, lang)) for f in sorted(twice)]
    failed = set(twice)
    for v in values:
        if str(v.get("field") or "") in twice:
            continue  # two readings for one parameter: neither is used
        error = apply_value(model, state, v, message, lang)
        if error:
            errors.append(error)
            failed.add(str(v.get("field") or ""))
    lql_parts = []
    if model == "lql":  # organs list, "all organs" from the ontology, consistency with the tumour site
        lql_after(state, old, message, lang, lql_parts)
    q = ("« ", " »") if lang == "fr" else ("“", "”")
    sep = " : " if lang == "fr" else ": "
    named = named_fields(model, state, message)
    noted, replaced = [], 0
    for g in ("inputs", "experiment"):
        for n, r in state[g].items():
            before = old[g].get(n)
            if r.get("origin") != "provided" or r == before:
                continue
            arrow = (f"{shown(n, before['value'], lang)} → " if before and before.get("value") is not None
                     and not same(before["value"], r["value"]) else "")
            how = f"{q[0]}{r['evidence']}{q[1]}" + (f"{sep}{r['relative']}" if r.get("relative") else "")
            warn = (t["not_named"] if arrow and (before.get("origin") == "provided" or before.get("accepted"))
                    and (g, n) not in named else "")
            replaced += bool(arrow and before.get("origin") == "provided")
            noted.append(f"**{label(n, lang)}{sep}{arrow}{shown(n, r['value'], lang)}** ({how}){warn}")
    changed_fields = {n for g in ("inputs", "experiment") for n in state[g] if state[g][n] != old[g].get(n)}
    changed = bool(changed_fields)
    kept = bool(KEEP.search(message)) and bool(state.get("unresolved"))  # "keep": the current value stays
    kept_text = t["kept"].format(names(state["unresolved"], lang)) if kept else ""
    state["unresolved"] = sorted(failed | (set() if kept else set(state.get("unresolved") or []) - changed_fields))
    hold = bool(HOLD.search(message))
    restricted = bool(ONLY.search(message))
    if ACCEPT_WORD.search(message) and restricted and not hold:  # "yes, only for the length": named fields only
        chosen = [(g, n) for g, n in named_fields(model, state, message) if (g, n) in pending(state)]
        for g, n in chosen:
            state[g][n]["accepted"] = True
    else:
        chosen = []
    propose_defaults(model, state)
    verdict = check(model, state, lang)
    # the model's own sentences and questions are not shown: every statement and question in the reply comes from
    # this deterministic state, so the reply cannot contradict what was retained
    parts = [t["noted"].format("; ".join(noted))] if noted else []
    if replaced >= 2:  # several stated values replaced at once: probably a new case
        parts.append(t["new_case"])
    if kept_text:
        parts.append(kept_text)
    if not (changed or errors or chosen or kept):
        parts.append(t["unchanged"])
    if errors:
        parts.append(t["unused"].format("; ".join(errors)))
    if chosen:
        parts.append(t["accepted_some"].format(", ".join(label(n, lang) for _, n in chosen)))
    if hold:
        parts.append(t["held"])
    parts += lql_parts
    if verdict["decision"] == "refuse":
        parts.append(refusal(model, lang, state))
    elif verdict["decision"] == "execute":
        key, question = lql_missing(state, lang) if model == "lql" else (None, None)
        if key:  # the kind of question asked still needs an answer
            state["lql"]["awaiting"] = key
            parts.append(question)
        elif not state["unresolved"]:
            if model == "lql" and lql_plan(state, lang):
                parts.append(lql_plan(state, lang))
            parts.append(t["ready"])  # a change or a question never runs the code in the same turn
    else:
        parts.append(clarify_text(model, state, verdict, lang))
    if state["unresolved"]:
        parts.append(t["blocked"].format(names(state["unresolved"], lang)))
    blocked = verdict["decision"] == "execute" or errors or state["unresolved"]
    decision = "clarify" if blocked and verdict["decision"] != "refuse" else verdict["decision"]
    return respond(model, lang, state, "\n\n".join(p for p in parts if p), decision=decision)


def api_example(model, lang):
    state = fresh(model, lang)
    base = json.loads((WS / "examples" / ("tls-complete.json" if model == "tls" else "lql-complete.json"))
                      .read_text(encoding="utf-8"))
    for group in ("inputs", "experiment"):
        for name, rec in base[group].items():
            state[group][name] = dict(rec, accepted=True, source="Example scenario (fictitious), stated and accepted")
    if model == "tls":
        state["experiment"]["n_days"]["value"], state["experiment"]["n_runs"]["value"] = 7, 5
    state["request"] = "Example scenario"
    out = json.loads(compute(model, lang, state))
    out["reply"] = T[lang]["example_done"]
    return json.dumps(out, ensure_ascii=False, default=str)
