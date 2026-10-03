# Vocabulaire sémantique TLS (première version)

`tls-vocabulary.ttl` représente en RDF/SKOS les 26 paramètres : noms français, unités lisibles, définitions. Les intentions énergie totale, énergie annualisée, énergie par longueur et puissance de pointe sont reliées à leurs indicateurs. Les classes distinguent scénario, paramètre, valeur fournie, hypothèse et sortie simulée.

`src/websemantic/semantics.py` produit et utilise ce vocabulaire dans le terminal, puis exporte chaque calcul en `semantics.ttl` avec valeurs, unités, statut d'acceptation et dérivations PROV-O. Le manifeste JSON reste la fiche complète de qualification. Le namespace est local au projet, pas un identifiant enregistré à w3id.

Ce premier graphe n'est pas encore un raisonneur OWL, ni un contrôle SHACL complet ou une cartographie automatique besoin/service. Les symboles d'unités sont explicites ; leur alignement QUDT reste à vérifier et implémenter. Le cas Ajaccio est un profil documentaire limité : contexte urbain et proxy d'altitude littorale 10 m (hypothèse choisie, pas moyenne mesurée). Les autres champs proviennent des valeurs par défaut TLS, jamais d'une prétendue observation locale.
