# Urban Eredan

## Contexte
Urban Eredan est un jeu de cartes qui se fait s'affronter deux équipes de combattants. Chaque équipe est composée de 4 combattants. Une partie est constituée d'au maximum 4 duels faisant s'opposer un membre de chaque équipe à chaque fois. La partie se termine soit lorsque l'un des deux joueurs est KO, soit à la fin des 4 duels, le gagnant étant le joueur avec le plus de vie restante.

## Composants principaux
- Cartes Champ de bataille : c'est le terrain commun sur lequel se résout chaque duel. Une carte comporte 3 cases, une par Zone : **Bitume**, **Hauteur**, **Souterrain**. Chaque case porte une valeur comprise entre -2 et 6.
  - Le dos de la carte comporte lui aussi 3 cases, mais **une seule y est colorée** : celle que la carte choisit de dévoiler, verte si sa valeur au recto est positive, rouge si elle est négative. Les deux autres restent grises, ce qui signifie « inconnu ». Ainsi un champ de bataille [2, 3, -2] qui dévoile sa troisième case a pour dos [gris, gris, rouge]. Ce dos donne une première information sur le terrain sans en révéler la valeur exacte.
  - La case dévoilée n'est jamais nulle : elle serait grise, donc indistinguable d'une case inconnue.
  - En moyenne, un champ de bataille comporte 2 cases vertes et une case grise ou rouge, avec des variantes plus extrêmes (tout vert, ou tout gris/rouge).
- Cartes Combattant : ce sont les membres de chaque équipe. Chaque Combattant possède les caractéristiques suivantes :
  - Nom
  - Puissance
  - Avantage : la liste des Zones (1 à 3 Zones parmi les 3) dont le Combattant tire parti. Il ajoute à sa Puissance la valeur des cases correspondantes du champ de bataille ; il ignore totalement les autres cases. Un Combattant à 3 Zones encaisse toute la carte, en bien comme en mal, et voit toujours la Zone dévoilée ; un Combattant à 1 Zone est un spécialiste, mais il n'a d'information sur son terrain que lorsque la Zone dévoilée est justement la sienne.
  - Dégâts
  - Pouvoir
- Suivi de Points de Vie (PV, matérialisé par une carte dans le jeu physique et par un compteur dans le jeu vidéo).

## Mise en place
- Chaque joueur récupère son équipe de 4 combattants et les dispose sur la table faces visibles.
  - Pour une partie initiation, les combattants sont distribués aléatoirement
  - Pour une partie avancée, les joueurs peuvent soit préconstruire leur équipe avec leur exemplaire du jeu, soit effectuer un draft avec l'ensemble des personnages présents dès le départ et un tour de bannissement où chaque joueur pourra retirer un personnage parmi ceux disponibles.
- Chaque joueur initie ses PV à 10
- Mélangez le deck de cartes Champ de bataille ; il est commun aux deux joueurs et servira de pioche à chaque duel
- Le premier joueur est désigné aléatoirement

## Pouvoir
Les pouvoirs des Combattants sont définis à partir d'un ou plusieurs mots clés auxquels peuvent être attribués des valeurs. Il existe trois sortent de mots clés :
- Effet : détermine ce que fait le pouvoir
- Condition : détermine sous quelle condition le pouvoir peut s'appliquer
- Modificateur : détermine combien de fois le pouvoir est appliqué

## Structure d'une partie
La partie se déroule comme une succession de duels. Chaque duel suit la structure suivante :
1. La carte Champ de bataille de la manche est piochée et posée **face cachée** : les deux joueurs découvrent son dos, c'est-à-dire la couleur de l'unique Zone dévoilée, et rien d'autre. Aucune valeur exacte n'est connue à ce stade.
2. Le premier joueur (J1) choisit son combattant et l'engage face visible
3. Le second joueur (J2) choisit son combattant, en connaissant celui que J1 vient d'engager
4. Une fois les deux Combattants engagés, le champ de bataille est révélé
5. Chaque Combattant encaisse la valeur des seules cases couvertes par son Avantage. Le champ de bataille est commun, mais les deux Combattants n'en lisent pas les mêmes cases.
6. En commençant par J1, les joueurs appliquent leurs pouvoirs. Il n'y a pas d'Energie dans cette version : chaque Pouvoir est toujours actif, seule sa condition de jeu peut l'empêcher de se déclencher.
7. La Puissance totale de chaque Combattant est définie par sa Puissance de base à laquelle s'ajoute la somme des cases de son Avantage, le tout modifié par les Pouvoirs activés des deux combattants
8. Le Combattant avec la meilleure Puissance totale remporte le duel. En cas d'égalité, les deux Combattants remportent le duel.
9. Le ou les Combattants ayant remporté le duel réduisent les PV adverses d'un montant égal à leurs Dégâts (éventuellement modifiés par les Pouvoirs)
10. S'il reste encore au moins 1 Combattant à chaque joueur et qu'aucun n'est KO (PV supérieur à 0), alors un nouveau duel commence. Le premier joueur du nouveau duel est le gagnant du duel précédent. En cas de double victoire, c'est J2 devient J1, et inversement.

## Fin de partie
Si après un duel, un joueur n'a plus de points de vie, il perd immédiatement la partie.
Après les 4 duels, le joueur avec le plus de vie restante remporte la partie.