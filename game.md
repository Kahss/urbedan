# Urban Eredan

## Contexte
Urban Eredan est un jeu de cartes qui se fait s'affronter deux équipes de combattants. Chaque équipe est composée de 4 combattants. Une partie est constituée d'au maximum 4 duels faisant s'opposer un membre de chaque équipe à chaque fois. La partie se termine soit lorsque l'un des deux joueurs est KO, soit à la fin des 4 duels, le gagnant étant le joueur avec le plus de vie restante.

## Composants principaux
- Dés : ce sont eux qui déterminent la Puissance et l'Énergie d'un Combattant pendant un duel. Ce sont des dés spéciaux à 6 faces ; chaque face porte une Puissance (0 à 6) et une Énergie (0 à 2), notées "X/Y". La Puissance sert à départager les deux Combattants du duel, l'Énergie détermine si le Pouvoir du Combattant s'active. Les répartitions des valeurs limitent la variance des résultats tout en restant aléatoires. Il existe trois dés, un par couleur :
  - rouge : plus orienté Puissance ; bleu : plus orienté Énergie ; violet : un mélange des deux
  - Le code couleur donne rapidement une idée a priori du type de ressource que le joueur peut s'attendre à recevoir.
  - Faces de chaque dé :
    - Rouge : 4/0 4/0 3/0 3/0 2/0 2/0
    - Bleu : 2/1 2/1 1/1 1/1 0/2 0/2
    - Violet : 3/1 3/0 2/1 2/0 1/0 1/1
- Cartes Combattant : ce sont les membres de chaque équipe. Un Combattant n'a pas de Puissance imprimée ; il possède les caractéristiques suivantes :
  - Nom
  - Dés personnels : le ou les dés qu'il lance pour déterminer sa Puissance et son Énergie
  - Dés adverses : le ou les dés qu'il donne à l'adversaire du duel, qui les ajoute à ses propres dés personnels
  - Dégâts
  - Pouvoir
  En moyenne, un Combattant a deux dés personnels et un dé adverse. Les dés servent de valeur d'ajustement : un Combattant peut être très fort en ayant trois dés personnels, mais donner en contrepartie deux dés à l'adversaire. De même, un Combattant peut être à double tranchant en offrant à l'adversaire la possibilité d'avoir plus d'Énergie via le dé bleu qu'il lui donne.
- Suivi de Points de Vie (PV, matérialisé par une carte dans le jeu physique et par un compteur dans le jeu vidéo).

## Mise en place
- Chaque joueur récupère son équipe de 4 combattants et les dispose sur la table faces visibles.
  - Pour une partie initiation, les combattants sont distribués aléatoirement
  - Pour une partie avancée, les joueurs peuvent soit préconstruire leur équipe avec leur exemplaire du jeu, soit effectuer un draft avec l'ensemble des personnages présents dès le départ et un tour de bannissement où chaque joueur pourra retirer un personnage parmi ceux disponibles.
- Chaque joueur initie ses PV à 10
- Les dés sont posés en réserve commune au centre de la table ; on y pioche les dés indiqués sur les cartes au moment de chaque duel
- Le premier joueur est désigné aléatoirement

## Pouvoir
Les pouvoirs des Combattants sont définis à partir d'un ou plusieurs mots clés auxquels peuvent être attribués des valeurs. Il existe trois sortent de mots clés :
- Effet : détermine ce que fait le pouvoir
- Condition : détermine sous quelle condition le pouvoir peut s'appliquer
- Modificateur : détermine combien de fois le pouvoir est appliqué

## Structure d'une partie
La partie se déroule comme une succession de duels. Chaque duel suit la structure suivante :
1. Le premier joueur (J1) choisit le Combattant qu'il engage
2. Le second joueur (J2) choisit le Combattant qu'il engage, en connaissant celui de J1
3. Chaque joueur récupère les dés personnels notés sur la carte de son Combattant, puis y ajoute les dés adverses notés sur la carte du Combattant d'en face
4. Chaque joueur lance l'ensemble de ses dés : la somme des Puissances obtenues donne sa Puissance de départ pour le duel, la somme des Énergies obtenues donne l'Énergie dont il dispose
5. Les joueurs regardent s'ils ont assez d'Énergie sur leurs dés pour l'activation de leur Pouvoir
6. En commençant par J1, les joueurs appliquent leurs pouvoirs si les conditions sont satisfaites (Énergie suffisante et condition de jeu)
7. La Puissance totale de chaque Combattant est celle obtenue au jet, éventuellement modifiée par les Pouvoirs activés des deux combattants
8. Le Combattant avec la meilleure Puissance totale remporte le duel. En cas d'égalité, les deux Combattants remportent le duel.
9. Le ou les Combattants ayant remporté le duel réduisent les PV adverses d'un montant égal à leurs Dégâts (éventuellement modifiés par les Pouvoirs)
10. S'il reste encore au moins 1 Combattant à chaque joueur et qu'aucun n'est KO (PV supérieur à 0), alors un nouveau duel commence. Le premier joueur du nouveau duel est le gagnant du duel précédent. En cas de double victoire, c'est J2 devient J1, et inversement.

## Fin de partie
Si après un duel, un joueur n'a plus de points de vie, il perd immédiatement la partie.
Après les 4 duels, le joueur avec le plus de vie restante remporte la partie.
