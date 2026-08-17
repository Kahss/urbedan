# Dés puissance via les personnages

Voici les modifications par rapport à la version actuelle :
- Dans cette version, il n'y a plus de cartes de Puissances
- Les personnages n'ont plus de valeur de puissance
- A la place, chaque personnage présente deux caractéristiques
  - Dés personnels : le ou les dés qui seront lancés par le personnage pour déterminer sa Puissance
  - Dés adverses : le ou les dés qui seront donnés à l'adversaire pour être ajoutés à ses propres dés personnels
- L'ordre du choix des personnages est effectué de façon identique
- Lorsque les deux personnages sont choisis, chaque joueur récupère les dés personnels noté sur la carte de son personnage, puis y ajoute les dés adverses du personnage adverse, puis lance le tout pour déterminer la puissance et l'énergie disponible pour le personnage pour le combat
- Les dés sont des dés spéciaux à 6 faces.
- Chaque face comporte les informations suivantes :
  - Puissance : valeur entre 0 et 6
  - Énergie : valeur entre 0 et 2
- Les répartitions des valeurs sont faites de façon à limiter la variance sur les résultats, tout en restant aléatoire
- Il y a trois dés, un par couleur, et il n'y a pas de déclinaison en teintes :
  - rouge : plus orienté puissance
  - bleu : plus orienté énergie
  - violet : un mélange des deux
- Le code couleur est là pour donner rapidement une idée a priori du type de ressource que le joueur peut s'attendre à recevoir
- Voici les définitions des faces de dés, avec la notation X/Y signifiant "X puissance et Y énergie" :
    - Rouge :  4/0	4/0	3/0	3/0	2/0	2/0
    - Bleu :   2/1	2/1	1/1	1/1	0/2	0/2
    - Violet : 3/1	3/0	2/1	2/0	1/0	1/1
- Pour la résolution du combat, les joueurs regardent s'ils ont assez d'énergie sur leurs dés pour l'activation de leurs pouvoirs, et le gagnant est désigné par la somme totale des puissances des dés du joueur éventuellement modifiées par les capacités
- Les dés servent de valeur d'ajustement pour les personnages : un personnage peut être très fort en ayant trois dés persos, mais à l'inverse donner deux dés à l'adversaire
- De même, un personnage peut être à double tranchant en donnant la possibilité à l'adversaire d'avoir plus d'énergie via le dé bleu qu'il lui donne
- En moyenne, les personnages ont deux dés personnels et un dé adverse
