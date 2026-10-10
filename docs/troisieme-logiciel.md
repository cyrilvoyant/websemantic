# Troisième logiciel : piste atmosphérique

## Choix après essais

**pyrcel 2.0.0 retenu pour intégration**, après les premiers essais réels. Les deux candidats ont exécuté un cas synthétique reproductible sous Windows ; preuves et limites dans [evaluation/candidates](../evaluation/candidates/README.md). Cela ne valide pas encore la distribution. ecape-parcel-py reste une alternative. Les audits ci-dessous décrivent la phase précédente.

## Demande du 6 octobre 2026

Étudier un remplacement de pvlib par un logiciel atmosphérique plus spécialisé. La connaissance préalable d’un code par les modèles est un facteur à contrôler ; le faible nombre d’utilisateurs ne démontre pas son absence des données d’apprentissage. Employer scénarios inédits, versions fixes et comparaisons appariées ; séparer documentation native et enrichissement.

## Candidat prioritaire à tester : ecape-parcel-py

Source : https://github.com/a-urq/ecape-parcel-py

Copie locale d’audit : work/candidates/ecape-parcel-py ; révision edddf4f68fe70cc8d81f309eb15d94b0f4fc16e1. Aucune modification ni publication sur le dépôt original. Licence MIT lue dans LICENSE : conserver copyright, texte et disclaimer dans les copies et le package. Le code tiers conserve sa licence ; la licence de WebSemantic ne le remplace pas.

Profil proposé : ascent d’une parcelle à partir d’un profil de pression, altitude, température, point de rosée et vent. Sorties : trajectoire thermodynamique et indicateurs de convection selon les capacités API réellement vérifiées. Comparaisons RMSD sur une même grandeur et grille verticale, pas sur une puissance électrique. Les modes avec/sans entraînement et pseudoadiabatique/adiabatique sont explicites.

Dépendances déclarées : ecape et metpy. API et conventions d’unités à vérifier à la révision clonée ; le README seul ne suffit pas. L’arborescence inspectée ne fournit pas de suite de tests dédiée. Prévoir fixtures sourcées et contrôles indépendants. Aucun résultat de calcul n’est encore validé dans WebSemantic.

Porte de choix : installation isolée sur Windows et Linux, calcul hors réseau sur profil figé, résultats finis et traçables, contrôle de grille/unités, cas physiques limites, licence des dépendances et coût. Échouer à cette porte entraîne un autre candidat ; ne pas activer le choix du menu avant intégration complète.

## Alternative : pyrcel

Source : https://github.com/darothen/pyrcel ; licence BSD-3-Clause, fichier LICENSE.md consulté. Modèle de parcelle nuageuse et activation d’aérosols. Profil temporel et sémantique riche ; dépendances déclarées nombreuses, notamment JAX/diffrax/equinox, avec compilation initiale des kernels. Installation Windows et coût à vérifier avant choix. Ni copie ni intégration de ce candidat à ce stade.

## Coordination et distribution

L’audit technique et les adaptateurs sont menés avec l’évaluation du périmètre et des questions de compétence du candidat. LQL-Equiv-web reste le second logiciel ; le troisième n’est pas encore arrêté. Les dépôts TLS/LQL et du candidat restent intacts. Les contrats, adaptateurs et notices tierces sont maintenus dans WebSemantic. Le package final inclut les deux nouveaux logiciels, leurs références versionnées et les exemples du guide après tests ; aucune intégration complète n’est revendiquée maintenant.

Mise à jour GitHub après chaque changement validé, en ne committant ni secrets ni les travaux concurrents d’un autre collaborateur. État et prochaine porte sont publiés dans le journal.
