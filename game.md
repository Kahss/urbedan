# Urban Eredan

## Contexte
Urban Eredan est un jeu de cartes qui se fait s'affronter deux équipes de combattants. Chaque équipe est composée de 4 combattants. Une partie est constituée d'au maximum 4 duels faisant s'opposer un membre de chaque équipe à chaque fois. La partie se termine soit lorsque l'un des deux joueurs est KO, soit à la fin des 4 duels, le gagnant étant le joueur avec le plus de vie restante.

## Composants principaux
- Cartes Bataille : c'est par elles que se résout chaque duel. Le deck compte 20 cartes distinctes, mélangées puis coupées en **2 pioches de 10** posées au centre de la table pour toute la partie.
  - Le **recto** porte une condition qui désigne le vainqueur de la bataille à partir des caractéristiques des deux Combattants engagés (par exemple « Force la plus haute », « Dextérité + Sagesse la plus haute », « Total des trois caractéristiques le plus haut »).
  - Le **verso** porte **une seule couleur**, choisie parmi les caractéristiques que la condition utilise : c'est la seule information disponible avant de piocher. L'indice est donc partiel, et parfois trompeur — un dos rouge annonce le plus souvent « Force la plus haute », mais peut aussi cacher « Force la plus basse », ou une condition où la Force n'est que secondaire.
  - Composition du deck : pour chacune des trois caractéristiques, 3 cartes « la plus haute », 1 carte « la plus basse », 1 carte « somme avec la caractéristique suivante » et 1 carte « la plus haute, égalité départagée par la caractéristique suivante », soit 18 cartes ; s'y ajoutent 2 cartes globales qui lisent les trois caractéristiques. Les dos se répartissent en 6 rouges, 7 verts et 7 bleus.
- Cartes Combattant : ce sont les membres de chaque équipe. Chaque Combattant possède les caractéristiques suivantes :
  - Nom
  - **Force** (rouge), **Dextérité** (vert) et **Sagesse** (bleu) : trois valeurs comprises entre 0 et 5, avec lesquelles il dispute les batailles. Le total des trois est compris entre 6 et 10 et est compensé par les Dégâts : un Combattant qui gagne souvent frappe moins fort. En pratique, le roster se tient entre 8 et 10 — en dessous, un Combattant perd trop souvent pour que ses Dégâts (plafonnés à 5) puissent compenser. Une valeur extrême est plus utile qu'une valeur moyenne : un 5 remporte les cartes « la plus haute » de sa couleur, un 0 remporte celles « la plus basse ».
  - Dégâts
- Suivi de Points de Vie (PV, matérialisé par une carte dans le jeu physique et par un compteur dans le jeu vidéo).

## Mise en place
- Chaque joueur récupère son équipe de 4 combattants et les dispose sur la table faces visibles.
  - Pour une partie initiation, les combattants sont distribués aléatoirement
  - Pour une partie avancée, les joueurs peuvent soit préconstruire leur équipe avec leur exemplaire du jeu, soit effectuer un draft avec l'ensemble des personnages présents dès le départ et un tour de bannissement où chaque joueur pourra retirer un personnage parmi ceux disponibles.
- Chaque joueur initie ses PV à 10
- Mélangez le deck de 20 cartes Bataille et coupez-le en 2 pioches de 10, faces cachées au centre de la table ; elles sont communes aux deux joueurs et servent à tous les duels de la partie
- Le premier joueur est désigné aléatoirement

## Pouvoirs
Cette version se joue sans Pouvoir : un Combattant n'est défini que par ses trois caractéristiques et ses Dégâts. Les Pouvoirs (et les mots clés de `pouvoirs.csv`) sont conservés en données pour une version ultérieure, mais ne sont pas utilisés.

## Structure d'une partie
La partie se déroule comme une succession de duels. Chaque duel suit la structure suivante :
1. Le premier joueur (J1) choisit son combattant et l'engage face visible
2. Le second joueur (J2) choisit son combattant, en connaissant celui que J1 vient d'engager
3. Les batailles se disputent alors une par une, **en commençant par J1 puis à tour de rôle** — l'ordre ne dépend pas de qui remporte les batailles :
   - le joueur dont c'est le tour choisit l'une des 2 pioches, en ne connaissant que la couleur au dos de sa carte du dessus
   - cette carte est révélée, sa condition est immédiatement résolue à partir des caractéristiques des deux Combattants engagés, et la carte est attribuée au joueur dont le Combattant l'emporte
   - si la condition ne sépare pas les deux Combattants, la **bataille est nulle** : la carte est défaussée et personne ne marque
4. Le duel s'arrête dès que l'un des Combattants a remporté **3 batailles**. Si **7 cartes** ont été révélées sans qu'aucun n'y parvienne, c'est le joueur ayant remporté le plus de batailles qui remporte le duel ; à égalité, les deux Combattants remportent le duel.
5. Le ou les Combattants ayant remporté le duel réduisent les PV adverses d'un montant égal à leurs Dégâts. Le score du duel (3-0 ou 3-2) ne modifie pas les Dégâts infligés.
6. Les cartes du duel (batailles remportées et batailles nulles) rejoignent la défausse commune. Si une pioche s'épuise, la défausse est mélangée et répartie sous les deux pioches.
7. S'il reste encore au moins 1 Combattant à chaque joueur et qu'aucun n'est KO (PV supérieur à 0), alors un nouveau duel commence. Le premier joueur du nouveau duel est le gagnant du duel précédent. En cas de double victoire, c'est J2 devient J1, et inversement.

## Fin de partie
Si après un duel, un joueur n'a plus de points de vie, il perd immédiatement la partie.
Après les 4 duels, le joueur avec le plus de vie restante remporte la partie.
