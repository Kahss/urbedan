# Urban Eredan

## Contexte
Urban Eredan est un jeu de cartes qui se fait s'affronter deux équipes de combattants. Chaque équipe est composée de 4 combattants. Une partie est constituée d'au maximum 4 duels faisant s'opposer un membre de chaque équipe à chaque fois. La partie se termine soit lorsque l'un des deux joueurs est KO, soit à la fin des 4 duels, le gagnant étant le joueur avec le plus de vie restante.

## Composants principaux
- Cartes Glyphes : ce sont les cartes qui vont permettre de booster les combattants au cours de chaque duel. Chaque Glyphe a deux propriété : une Puissance et une Energie. En terme de notation, un Glyphe avec une Puissance de X et une Energie de Y est noté "X/Y" La Puissance s'ajoute à la puissance du combattant, et l'Energie détermine combien de Capacités du combattants sont activées pendant le duel. Elles sont réparties comme suit :
  - 4 cartes 6 Puissances / 0 Energie
  - 4 cartes 4 Puissances / 1 Energie
  - 4 cartes 2 Puissance / 2 Energies
  - 4 cartes 0 Puissance / 3 Energies
- Cartes Combattant : ce sont les membres de chaque équipe. Chaque Combattant possède les caractéristiques suivantes :
  - Nom
  - Puissance
  - Dégâts
  - Pouvoir
- Suivi de Points de Vie (PV, matérialisé par une carte dans le jeu physique et par un compteur dans le jeu vidéo).

## Mise en place
- Chaque joueur récupère son équipe de 4 combattants et les dispose sur la table faces visibles.
  - Pour une partie initiation, les combattants sont distribués aléatoirement
  - Pour une partie avancée, les joueurs peuvent soit préconstruire leur équipe avec leur exemplaire du jeu, soit effectuer un draft avec l'ensemble des personnages présents dès le départ et un tour de bannissement où chaque joueur pourra retirer un personnage parmi ceux disponibles.
- Chaque joueur initie ses PV à 10
- Mélangez le deck de cartes Glyphes ; il est commun aux deux joueurs et servira de pioche à chaque duel
- Chaque joueur pioche un premier Glyphe, qui constitue sa main de départ
- Le premier joueur est désigné aléatoirement

## Pouvoir
Les pouvoirs des Combattants sont définis à partir d'un ou plusieurs mots clés auxquels peuvent être attribués des valeurs. Il existe trois sortent de mots clés :
- Effet : détermine ce que fait le pouvoir
- Condition : détermine sous quelle condition le pouvoir peut s'appliquer
- Modificateur : détermine combien de fois le pouvoir est appliqué

## Structure d'une partie
La partie se déroule comme une succession de duels. Chaque duel suit la structure suivante :
1. Chaque joueur pioche un Glyphe dans la pioche commune, qui s'ajoute à celui déjà en main (non joué lors de la manche précédente) : il a donc 2 Glyphes disponibles pour cette manche
2. Le premier joueur (J1) choisit son combattant et lui associe l'un de ses 2 Glyphes disponibles face cachée (l'autre reste en main pour la manche suivante), en connaissant sa propre main (mais pas celle de l'adversaire)
3. Le second joueur (J2) choisit son combattant et lui associe l'un de ses 2 Glyphes disponibles face cachée, dans les mêmes conditions
4. Une fois les deux couples Combattant/Glyphe choisis, les Glyphes associés sont révélés et automatiquement joués face à face
5. En commençant par J1, les joueurs appliquent leurs pouvoirs si les conditions sont satisfaites (nombre d'énergie et condition de jeu)
6. La Puissance totale de chaque Combattant est définie par sa Puissance de base à laquelle s'ajoute la puissance du Glyphe qui lui est associé, le tout modifié par les Pouvoirs activés des deux combattants
7. Le Combattant avec la meilleure Puissance totale remporte le duel. En cas d'égalité, les deux Combattants remportent le duel.
8. Le ou les Combattants ayant remporté le duel réduisent les PV adverses d'un montant égal à leurs Dégâts (éventuellement modifiés par les Pouvoirs)
9. S'il reste encore au moins 1 Combattant à chaque joueur et qu'aucun n'est KO (PV supérieur à 0), alors un nouveau duel commence. Le premier joueur du nouveau duel est le gagnant du duel précédent. En cas de double victoire, c'est J2 devient J1, et inversement.

## Fin de partie
Si après un duel, un joueur n'a plus de points de vie, il perd immédiatement la partie.
Après les 4 duels, le joueur avec le plus de vie restante remporte la partie.