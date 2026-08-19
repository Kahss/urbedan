# Version avec duo de personnages

- Cette version change beaucoup de choses par rapport à la version de base
- Dans cette version, le jeu se passe en une série de 4 affrontements, mais cette fois, chaque affrontement fait intervenir deux personnages de chaque équipe
- Voici la boucle de gameplay :
  - La carte bataille du tour est révélée.
  - Les deux joueurs choisissent simultanément les deux personnages qu'ils envoient à la bataille
  - Les capacités de chaque personnages sont appliquées si possible
  - Le duo de personnage avec la somme de puissance la plus élevée remporte le duel
  - Le perdant perd un nombre de PV égaux à la somme des dégâts des personnages adverses
- Concernant les éléments de jeu :
  - Les personnages gardent leurs caractéristiques : puissance, dégâts et capacité
  - Il n'y a plus d'élément permettant d'augmenter la puissance des personnages joué
  - Les capacités ne nécessitent plus d'énergie pour être activées
  - Les cartes batailles ont un effet appliqué par le joueur qui remporte la bataille
    - Par exemple : +2 dégâts, +2 PV, le joueur adverse révèle un de ces deux choix au tour suivant
- Chaque personnage ne peut être utilisé que deux fois tout au long de la partie.
  - Dans un jeu physique, les cartes seraient inclinées pour montrer qu'elles ont déjà été utilisées une fois.
  - Visuellement, tu devras le représenter par exemple avec des ronds de couleur sous les cartes.
  - Ce point de règle permet de créer deux nouvelles conditions d'activation de pouvoir : première fois et seconde fois, en fonction de si le personnage est joué pour la première ou la seconde fois de la partie
- Concernant l'équilibrage, un personnage est considéré comme équilibré non pas s'il remporte environ la moitié de ses duels, mais plutôt si environ la moitié des équipes dont il fait partie remporte la partie. Cela permet de créer des personnages ayant intérêt à perdre, par exemple avec des capacités ayant des effets en cas de défaite

# Liste des personnages

Nom	Puissance	Dégâts	Pouvoir
Barbare	4	6	Contrecoup : -2 PV
Barde	1	1	Si puissance alliée >= 3 : Dégâts +3
Clerc	2	3	Défaite : +3 PV
Druide	1	2	Second tour : +4 Puissance, +4 Dégâts
Guerrier	3	4	Aucun effet
Moine	3	2	Patience : +1 dégâts
Paladin	4	3	Vengeance : +2 Puissance, +2 Dégâts
Ranger	2	3	Patience : -1 Dégâts
Voleur	1	1	Si au moins un adversaire avec Puissance de base >= 4 : Puissance +4
Ensorceleur	2	1	Si au moins un adversaire avec dégâts de base >= 3 : Dégâts -3
Sorcier	4	2	Victoire : Vampirisme 2
Mage	3	2	Dégâts -2

# Batailles

L'effet d'une bataille est appliqué uniquement par le joueur qui remporte le duel

Nom	Effet
A la loyale	Aucun effet
Dans les bas-fonds	Dégâts +2
Soigner les blessés	+2 PV
Repérage	Lors du prochain duel, l'adversaire révèle un de ses deux personnages au choix
Second souffle	Rend une utilisation à un personnage
Planification	Patience : +1 PV
Dépasser ses limites	Lors du prochain duel, toutes les conditions de capacités sont considérées validées