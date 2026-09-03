# Urban Eredan

## Contexte
Urban Eredan est un jeu de cartes qui se fait s'affronter deux équipes de combattants. Chaque équipe est composée de 4 combattants. Une partie est constituée d'au maximum 4 duels faisant s'opposer un membre de chaque équipe à chaque fois. La partie se termine soit lorsque l'un des deux joueurs est KO, soit à la fin des 4 duels, le gagnant étant le joueur avec le plus de vie restante.

## Composants principaux
- Cartes Puissance : ce sont les cartes qui vont permettre de booster les combattants au cours de chaque duel, piochées en "stop ou encore" (voir "Structure d'une partie"). Chaque Carte Puissance a deux propriétés : une Puissance (entre 0 et 2) et des points de Malus (entre 0 et 2). Le tas, remélangé à chaque duel, est réparti comme suit :
  - 3 cartes Destin : 2 Puissance / 0 Malus
  - 7 cartes Chance : 1 Puissance / 0 Malus
  - 7 cartes Péripétie : 1 Puissance / 1 Malus
  - 3 cartes Malheur : 0 Puissance / 2 Malus
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
- Le premier joueur est désigné aléatoirement

## Pouvoir
Les pouvoirs des Combattants sont définis à partir d'un ou plusieurs mots clés auxquels peuvent être attribués des valeurs. Il existe trois sortent de mots clés :
- Effet : détermine ce que fait le pouvoir
- Condition : détermine sous quelle condition le pouvoir peut s'appliquer
- Modificateur : détermine combien de fois le pouvoir est appliqué

Le Pouvoir d'un Combattant est toujours actif. Le modificateur "Par carte piochée" (et ses variantes adverse / en jeu) multiplie la valeur de l'effet par le nombre de Cartes Puissance piochées pendant la phase de pioche du duel (voir ci-dessous), plafonné pour l'équilibrage.

## Structure d'une partie
La partie se déroule comme une succession de duels. Chaque duel suit la structure suivante :
1. Le premier joueur (J1) choisit son combattant, face cachée
2. Le second joueur (J2) choisit son combattant, face cachée, dans les mêmes conditions
3. Une fois les deux Combattants choisis, ils sont révélés face à face et la phase de pioche "stop ou encore" commence : mélangez un tas de 20 Cartes Puissance (3 Destin, 7 Chance, 7 Péripétie, 3 Malheur)
4. À tour de rôle, en commençant par J1 et jusqu'à ce que les deux joueurs se soient arrêtés, chaque joueur pioche une Carte Puissance dans ce tas, ou choisit de s'arrêter :
   - Un joueur peut choisir de s'arrêter à tout moment
   - Si la somme des Malus de ses cartes piochées devient supérieure ou égale à 3, il est obligé de s'arrêter
   - Un joueur qui s'est arrêté (volontairement ou non) ne peut plus piocher de nouvelle carte pour la suite du duel
5. Une fois les deux joueurs arrêtés, les joueurs appliquent leurs pouvoirs si les conditions sont satisfaites
6. La Puissance totale de chaque Combattant est définie par sa Puissance de base à laquelle s'ajoute la somme des Puissances de ses cartes piochées (annulée si la somme de ses Malus est supérieure ou égale à 3 ; la Puissance de base reste alors acquise), le tout modifié par les Pouvoirs activés des deux combattants
7. Le Combattant avec la meilleure Puissance totale remporte le duel. En cas d'égalité, les deux Combattants remportent le duel.
8. Le ou les Combattants ayant remporté le duel réduisent les PV adverses d'un montant égal à leurs Dégâts (éventuellement modifiés par les Pouvoirs)
9. S'il reste encore au moins 1 Combattant à chaque joueur et qu'aucun n'est KO (PV supérieur à 0), alors un nouveau duel commence. Le premier joueur du nouveau duel est le gagnant du duel précédent. En cas de double victoire, c'est J2 devient J1, et inversement.

## Fin de partie
Si après un duel, un joueur n'a plus de points de vie, il perd immédiatement la partie.
Après les 4 duels, le joueur avec le plus de vie restante remporte la partie.