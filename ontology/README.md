# Vocabulaire sémantique TLS (première version)

`tls-vocabulary.ttl` représente en RDF/SKOS les 26 paramètres : noms français, unités lisibles, définitions. Les intentions énergie totale, énergie annualisée, énergie par longueur et puissance de pointe sont reliées à leurs indicateurs. Les classes distinguent scénario, paramètre, valeur fournie, hypothèse et sortie simulée.

`src/websemantic/semantics.py` construit ce vocabulaire à partir du descripteur sélectionné et l’utilise dans le terminal, puis exporte chaque calcul en `semantics.ttl` avec valeurs, unités, statut d'acceptation et dérivations PROV-O. Le manifeste JSON reste la fiche complète de qualification. Le namespace est local au projet, pas un identifiant enregistré à w3id.

Ce premier graphe n'est pas encore un raisonneur OWL, ni un contrôle SHACL complet ou une cartographie automatique besoin/service. Les symboles d'unités sont explicites ; leur alignement QUDT reste à vérifier et implémenter. Les lieux et les sources géographiques sont déclarés dans le descripteur TLS. Les valeurs proposées restent des hypothèses non calibrées, à accepter explicitement ; les rapports sur l’air ambiant et les accidents ne deviennent pas des probabilités d’événements en tunnel.
