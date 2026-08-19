# Version avec résolution par cartes "bataille"

## Modification par rapport à la version de base

- Dans cette version, la résolution du combat se fait par la révélation de plusieurs cartes "bataille" une fois que les deux personnages ont été choisis
- Les personnages n'ont plus de caractéristiques puissance. A la place, ils ont trois caractéristiques : Force (rouge), Dextérité (vert) et Sagesse (bleu)
- Chaque caractéristique peut avoir une valeur entre 0 et 5
- Elles sont utilisées pour remporter les cartes batailles. Le premier personnage à remporter 3 batailles remporte le duel
- Une carte bataille contient les éléments suivants :
  - recto : une conditi on pour définir qui la remporte. Par exemple : "force la plus haute" ou "valeur maximale parmis les trois caractéristiques"
  - verso : une couleur parmi les trois caractéristiques (rouge, vert ou bleu). La couleur est un indice pour dire "cette caractéristique est utilisée pour résoudre la bataille"
- Pendant toute la partie, il y a 2 pioches de cartes batailles au centre de la table.
- Le déroulé du tour se passe donc comme suit :
  - J1 choisit son perso
  - J2 choisit son perso
  - Tant qu'aucun joueur n'a remporté au moins 3 batailles, en commençant par J1 puis à tour de rôle
    - le joueur choisit quelle carte bataille il pioche parmis les deux disponibles
    - la carte choisit est révélée, sa condition est résolue et elle est attribuée au joueur correspondant
  - Le gagnant du round inflige ses dégâts à l'adversaire
- Pour une première version, il n'y a pas de pouvoirs sur les personnages, uniquement les trois caractéristiques

## Système de capacités

- Chaque personnage à une capacité lui permettant d'influer sur le cours de la partie
- Les capacités peuvent être composées de 3 parties :
  - une condition (facultatif) : définit quand est-ce que la capacité peut être activée
    - victoire : le personnage doit remporter la bataille
    - défaite : le personnage doit perdre la bataille
    - premier : le joueur doit être J1
    - second : le joueur doit être J2
    - vengeance : le joueur doit avoir perdu sa bataille lors du duel précédent
    - confiance : le joueur doit avoir remporté sa bataille lors du duel précédent
  - un effet (obligatoire) : définit la capacité elle-même
    - vampirisme X : l'adverse perd X PV, le joueur en gagne X
    - +X PV : le joueur gagne X PV
    - -X PV : l'adversaire perd X PV
    - +X dégâts : les dégâts du personnage sont augmentés de X
    - -X dégâts : les dégâts du personnage adverse sont diminués de X
    - initiative : le personnage remporte les égalités
    - annule couleur : la caractéristique de la couleur spécifiée du personnage adverse est égale à 0 pour ce duel
  - un multiplicateur (facultatif) : définit combien de fois l'effet doit être appliqué
    - patience : multiplie l'effet par le nombre de round déjà joués
    - impatience : multiplie l'effet par le nombre de round qui restent à jouer
    - par bataille perdue : multiplie l'effet par le nombre de batailles perdues
    - par bataille remportée : multiplie l'effet par le nombre de batailles remportées