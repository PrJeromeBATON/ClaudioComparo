
# 2026 11 20 _ Claudio Comparo

Un exemple d'application créée avec Claude (free, Sonnet 5.5, Moyen) avec la conversation correspondante.

L'application sert à comparer des cours de différentes valeurs (actions, crypto, métaux).

Voir le fichier conversation.txt pour les prompts successifs ( identifiés par - ).

## Demandes successives

- Créé une application python avec streamlit qui permette de comparer les cours de BTC, ETH, or et argent dans le temps.

- il n'y a pas de graphique, voici une partie des logs
ERROR ['BTC-USD']: Exception('BTC-USD: No timezone found, symbol may be delisted')
ERROR ['EURUSD=X']: Exception('EURUSD=X: No timezone found, symbol may be delisted')

- le bouton " Rafraîchir les données" ne fonctionne pas car streamlit n'a pas de methode "rerun". Corriges

- je veux aussi pouvoir ajouter des assets en tapant leur nom ou  leur code, proposes l'autocomplétion

- Je veux pouvoir comparer les prix (par défaut) et les performances base 100. Fais deux graphiques

- la liste de valeur se comporte mal. On peut ajouter qu'une valeur supplémentaire et non pas plusieurs. De plus leur valeurs par défaut reviennent après avoir été supprimées.
Change le comportement. Et garde en stockage local html la sélection de valeurs de façon à les retrouver quand on revient sur l'application

## Constatations

Le fichier requirements.txt est fourni. Il est rappelé la syntaxe d'utilisation : une bonne chose.

Au premier jet, cela ne fonctionnait pas : pas  de chart !

Au second jet, il y avait deux charts : "Performance comparée (base 100)" et "Corrélation des rendements hebdomadaires", que je n'ai pas demandés et qui ne sont pas "grand public"
Le choix de devise de référence n'est pas demandé mais c'est utile

Les widgets pour l'ajout de valeur devraient être sous la liste de ceux en cours d'utilisation.

Proposer l'échelle logarithmique est une bonne idée.

Le code créé est clair et utilise l'anglais. Il est commenté en français. Incohérent.

Des surprises quant à l'UX, avec des comportements de l'appli qui ne nous paraissent pas naturels (voir la conversation).

## Ressenti / conclusion

J'y suis allé en mode naïf++ puisque je donnais un contexte technique initial que je connais et utilise.

C'est extrêmement intéressant comme résultat et utilisable après quelques itérations.

Sur cette appli simple, il m'a fallu tester différents comportements.
Cette étape ne peut pas être confiée à cet outil à ce jour.

Le travail change, mais l'humain est toujours nécessaire.
Et pour la petite histoire, on ne me demande plus ce cours en ce moment.
