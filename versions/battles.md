# Version avec résolution par cartes "bataille"

- Dans cette version, la résolution du combat se fait par la révélation de plusieurs cartes "bataille" une fois que les deux personnages ont été choisis
- Les personnages n'ont plus de caractéristiques puissance. A la place, ils ont trois caractéristiques : Force (rouge), Dextérité (vert) et Sagesse (bleu)
- Chaque caractéristique peut avoir une valeur entre 0 et 5
- Elles sont utilisées pour remporter les cartes batailles. Le premier personnage à remporter 3 batailles remporte le duel
- Une carte bataille contient les éléments suivants :
  - recto : une condition pour définir qui la remporte. Par exemple : "force la plus haute" ou "valeur maximale parmis les trois caractéristiques"
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