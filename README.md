# Urban Eredan — Prototype (version « cartes Bataille »)

Prototype jouable en solo (vs IA) du jeu de societe Urban Eredan (`game.md`), dans la
variante decrite par `versions/battles.md` : un duel ne se resout plus par une comparaison
de Puissance, mais en remportant **3 batailles** revelees une par une depuis deux pioches
communes. Backend Python (moteur de regles + IA), frontend web (HTML/CSS/JS, jouable
uniquement au clic).

## Ce qui change par rapport a la version de reference

- Les cartes **Glyphes** et l'**Energie** disparaissent ; les Pouvoirs sont remplaces par
  un systeme de **Capacites** (une par Combattant, cf. plus bas).
- Un Combattant n'a plus de Puissance : il porte trois caracteristiques, **Force**
  (rouge), **Dexterite** (vert) et **Sagesse** (bleu), chacune de 0 a 5, plus ses Degats
  et sa Capacite.
- Un deck de **21 cartes Bataille**, **remelange et recoupe en 2 pioches au debut de chaque
  duel**, est pose au centre de la table. Le recto porte la condition qui designe le
  vainqueur de la bataille ; le verso ne montre qu'**une couleur**, choisie parmi les
  caracteristiques que la condition utilise.
- Le premier Combattant a remporter **3 batailles** remporte le duel et inflige ses
  Degats. Une bataille que la condition ne tranche pas est **nulle** : personne ne marque.
- Sur l'ecran de selection, un bouton **Equipe aleatoire** tire 4 Combattants au hasard :
  c'est la « partie initiation » de `game.md`, ou les Combattants sont distribues
  aleatoirement.

## Lancer le jeu

Le projet est gere avec [uv](https://docs.astral.sh/uv/) :

```
uv run python backend/app.py
```

Puis ouvrir http://127.0.0.1:5000/ dans un navigateur.

Le serveur Flask sert a la fois l'API de jeu (`/api/...`) et les fichiers statiques du
frontend (`frontend/`). Une seule partie est active a la fois (etat en memoire, adapte a
un usage solo local).

## Structure du projet

```
data/combattants.json       Liste des Combattants jouables (editable a la main)
backend/
  app.py                    Serveur Flask (API REST)
  engine/
    batailles.py            Les 21 cartes Bataille, leur resolution et les 2 pioches
    capacites.py            Le vocabulaire des Capacites (condition / effet / multiplicateur)
    models.py               Combattants, Joueurs
    ia.py                   Heuristique de l'IA (Combattant + choix de pioche)
    game.py                 Orchestration d'une Partie (mise en place, duels, batailles)
frontend/
  index.html / style.css / app.js   Interface (100% cliquable, sans framework)
generate_metagame.py        Simulation IA contre IA : % de victoire par Combattant
```

## Les 21 cartes Bataille

Definies dans `backend/engine/batailles.py` (`MODELES`), avec leur nom, leur condition et
la couleur de leur dos. Le deck est structure de facon symetrique : chaque caracteristique
est la caracteristique principale de 6 cartes, et les 3 dernieres cartes lisent les trois
caracteristiques.

| Type de condition | Exemplaires | Exemple |
| --- | --- | --- |
| `max` : la caracteristique la plus haute l'emporte | 3 par caracteristique | Bras de fer — Force la plus haute |
| `min` : la plus basse l'emporte | 1 par caracteristique | Passage etroit — Force la plus basse |
| `somme` : la somme de deux caracteristiques la plus haute | 1 par caracteristique | Escalade sauvage — Force + Dexterite la plus haute |
| `max_departage` : la plus haute, puis une seconde caracteristique en cas d'egalite | 1 par caracteristique | Poigne et sang-froid — Force la plus haute ; a egalite, Sagesse |
| `total` : le total des trois le plus haut | 1 | Melee generale |
| `meilleure` : la meilleure des trois la plus haute | 1 | Coup d'eclat |
| `pire` : celui dont la plus petite des trois est la plus faible **perd** | 1 | Maillon faible |

Les caracteristiques tournent en cycle (Force → Dexterite → Sagesse → Force) pour les
sommes et les departages, de sorte que les trois groupes de 6 cartes soient rigoureusement
equivalents : aucune caracteristique n'est structurellement meilleure qu'une autre.

**Le dos** d'une carte est une des couleurs que sa condition lit, fixee une fois pour
toutes (comme une carte imprimee). Les dos se repartissent exactement en **7 rouges,
7 verts et 7 bleus** : le choix d'une pioche plutot que l'autre ne favorise a priori
aucune caracteristique. Un dos rouge cache ainsi 3 fois « Force la plus haute », mais
aussi « Force la plus basse », « Sagesse + Force la plus haute », « Dexterite la plus
haute, a egalite Force » et « Maillon faible » : l'indice oriente sans jamais garantir.

`Maillon faible` est le contrepoids des cartes `min` : ces dernieres recompensent un 0,
tandis que `Maillon faible` le punit. Une caracteristique laissee a 0 reste payante, mais
plus gratuitement.

## Les Capacites

Chaque Combattant porte une **Capacite**, composee de trois parties (cf. `game.md` et
`backend/engine/capacites.py`) : une **condition** facultative, un **effet** obligatoire et
un **multiplicateur** facultatif. Le vocabulaire complet, seul autorise par le moteur :

| Partie | Mot cle | Effet |
| --- | --- | --- |
| Condition | `victoire` / `defaite` | le Combattant doit remporter / perdre son duel |
| Condition | `premier` / `second` | le joueur doit etre J1 / J2 de ce duel |
| Condition | `vengeance` / `confiance` | le joueur doit avoir perdu / remporte son duel precedent |
| Effet | `vampirisme` X | l'adversaire perd X PV, le joueur en gagne X |
| Effet | `pv_soi` X / `pv_adverse` X | le joueur gagne X PV / l'adversaire perd X PV |
| Effet | `degats_soi` X / `degats_adverse` X | les Degats du Combattant / du Combattant adverse sont modifies de X |
| Effet | `initiative` | le Combattant remporte les batailles que la condition ne tranche pas |
| Effet | `annule_couleur` (couleur) | la caracteristique de cette couleur tombe a 0 chez l'adversaire, pour tout le duel |
| Multiplicateur | `patience` / `impatience` | x le nombre de duels joues / restants, celui-ci compris (1 a 4) |
| Multiplicateur | `par_bataille_remportee` / `par_bataille_perdue` | x le nombre de batailles gagnees / perdues dans ce duel |

Deux familles d'effets, qui n'agissent pas au meme moment :

- `initiative` et `annule_couleur` sont **figes des que les deux Combattants sont engages**,
  avant la premiere carte revelee : ils changent la facon dont les batailles se resolvent.
  Le moteur refuse donc de les associer a une condition qui depend de l'issue du duel
  (`victoire`, `defaite`) ou a un multiplicateur — il n'y a rien a multiplier.
- les autres effets s'appliquent **a la resolution du duel** : les modificateurs de Degats
  sont pris en compte avant que les Degats ne soient retires (plancher a 0), puis les PV
  sont ajustes (ils peuvent depasser 10).

Ces regles sont verifiees au chargement de `data/combattants.json` : une capacite mal
formee (mot cle inconnu, valeur manquante, passif conditionne a l'issue du duel) fait
echouer le demarrage avec un message explicite.

Le roster fourni couvre l'ensemble du vocabulaire — chacune des 6 conditions, des 7 effets
et des 4 multiplicateurs apparait au moins une fois :

| Combattant | Force / Dexterite / Sagesse | Total | Degats | Capacite |
| --- | --- | --- | --- | --- |
| Riff | 2 / 4 / 4 | 10 | 3 | Premier : +1 Degat |
| Nova | 2 / 1 / 5 | 8 | 3 | Annule la Sagesse adverse |
| Grind | 4 / 5 / 1 | 10 | 2 | Confiance : +2 Degats |
| Blaze | 4 / 3 / 2 | 9 | 3 | Vengeance : +3 Degats |
| Iron | 5 / 0 / 4 | 9 | 3 | -2 Degats adverses |
| Cobra | 2 / 5 / 1 | 8 | 5 | Confiance : Vampirisme 1 |
| Echo | 1 / 5 / 4 | 10 | 2 | Initiative |
| Vex | 1 / 2 / 5 | 8 | 4 | Defaite : -2 PV adverses |
| Mirage | 2 / 2 / 4 | 8 | 4 | Second : Annule la Dexterite adverse |
| Surge | 3 / 2 / 3 | 8 | 5 | +1 Degat par duel joue |
| Jab | 5 / 4 / 0 | 9 | 4 | Second : +3 Degats |
| Buzzer | 1 / 4 / 4 | 9 | 2 | -1 PV adverse par bataille remportee |
| Verve | 0 / 3 / 5 | 8 | 5 | Victoire : +3 PV |
| Gambit | 3 / 0 / 5 | 8 | 3 | +1 PV par bataille remportee |
| Nitro | 3 / 5 / 0 | 8 | 5 | +1 Degat par duel restant |
| Cascade | 5 / 3 / 1 | 9 | 3 | Defaite : +2 PV |
| Mime | 3 / 4 / 2 | 9 | 2 | Annule la Force adverse |
| Verrou | 5 / 2 / 2 | 9 | 2 | -1 Degat adverse par bataille perdue |
| Furet | 1 / 5 / 2 | 8 | 5 | Victoire : Vampirisme 1 |
| Suture | 1 / 3 / 5 | 9 | 2 | Defaite : +1 PV par duel joue |
| Toph | 5 / 1 / 3 | 9 | 4 | Vengeance : Initiative |
| Loup | 5 / 1 / 2 | 8 | 3 | Victoire : Vampirisme 2 |

Une Capacite est un cout comme un autre : elle se paie sur les caracteristiques et les
Degats. `Annule une couleur` est ainsi le contrepoids des profils extremes que le deck
favorise — un 5 remporte trois cartes de sa couleur, mais tombe a 0 devant Nova, Mirage ou
Mime.

## Editer / ajouter des Combattants

`data/combattants.json` peut etre modifie a la main puis est recharge automatiquement au
lancement d'une nouvelle partie (pas besoin de redemarrer le serveur).

```json
{
  "id": "identifiant_unique",
  "nom": "Nom affiche",
  "archetype": "texte narratif, ignore par le moteur",
  "description": "texte narratif, ignore par le moteur",
  "force": 5,
  "dexterite": 1,
  "sagesse": 3,
  "degats": 3,
  "capacite": {
    "condition": "vengeance",
    "effet": { "type": "degats_soi", "valeur": 3 },
    "multiplicateur": null
  }
}
```

- `force` / `dexterite` / `sagesse` : entiers de 0 a 5 (le moteur refuse toute valeur hors
  de cet intervalle au chargement).
- `degats` : PV retires a l'adversaire quand le Combattant remporte son duel.
- `capacite` : `condition` et `multiplicateur` peuvent valoir `null` ; `effet` est
  obligatoire et porte un `type`, une `valeur` entiere (sauf `initiative`) et, pour
  `annule_couleur`, une `couleur` (`rouge`, `vert` ou `bleu`). Le libelle imprime sur la
  carte est genere a partir de ces trois champs : il ne peut pas mentir sur l'effet reel.

### Equilibrer un Combattant

Trois leviers se compensent : les **caracteristiques** et la **Capacite** determinent la
frequence a laquelle un Combattant gagne ses duels, les **Degats** paient cette frequence.
Le roster fourni se tient entre 8 et 10 de total : en dessous, un Combattant perd trop
souvent pour que ses Degats (plafonnes a 5) puissent compenser. Trois proprietes guident la
repartition :

- **Les valeurs extremes valent mieux que les valeurs moyennes** : un 5 remporte les
  3 cartes « la plus haute » de sa couleur, et un 0 remporte celle « la plus basse » — au
  prix de `Maillon faible`, qui fait perdre la bataille a celui dont la plus petite
  caracteristique est la plus faible, et au prix des Capacites `annule_couleur`, qui font
  tomber une caracteristique a 0.
- **Un total eleve, ou une Capacite forte, doit se payer en Degats** : le roster fourni va
  de 2 Degats (profils qui gagnent 44 a 79 % de leurs duels) a 5 Degats (profils a 36 a
  40 %).
- **Une Capacite multipliee coute cher** : `patience` et `impatience` valent 2,5 fois
  l'effet en moyenne, `par bataille remportee`/`perdue` environ 1,5 fois. Reservez-les aux
  profils fragiles, qui ont de la marge sur leurs Degats pour les payer.

Le roster fourni (22 Combattants) a ete regle de cette facon : chaque Combattant inflige
en moyenne autant de PV qu'il en subit, a **0,23 PV par duel** pres (mesure par simulation
sur les 462 rencontres ordonnees possibles, dans les 4 numeros de duel et les 4 historiques
de duel precedent). Les Combattants gagnent de 36 % (Verve) a 79 % (Mime) de leurs duels :
c'est le prix paye en Degats qui remet tout le monde a egalite, pas le taux de victoire.

## IA

`engine/ia.py` :

- **Choix du Combattant** : tire au hasard parmi ceux qui n'ont pas encore combattu ;
  l'IA ne contre-choisit pas le Combattant adverse.
- **Choix de la pioche** : c'est la seule decision reellement informee du duel. L'IA ne
  connait de chaque pioche que la couleur au dos de sa carte du dessus, mais elle connait
  la composition du deck et voit les cartes deja revelees : elle sait donc exactement
  quelles cartes dorment encore dans les deux pioches, sans savoir laquelle est ou. Pour
  chaque pioche, elle resout toutes les cartes encore en jeu portant cette couleur contre
  les caracteristiques des deux Combattants engages — celles du duel, une couleur
  eventuellement annulee par une Capacite — et l'Initiative eventuelle des deux camps, puis
  retient la pioche de meilleure esperance (+1 bataille gagnee, -1 perdue, 0 nulle). Les
  egalites sont tranchees au hasard.

L'IA ne tient pas compte des Capacites dans le choix de son Combattant (elle le tire au
hasard) : seules celles qui changent la resolution des batailles entrent dans son calcul.

Le joueur humain dispose de la meme information : le deck est liste sur l'ecran de
selection, et le rapport de bataille du duel en cours rappelle quelles cartes sont deja
sorties.

## Hypotheses et choix d'implementation

`versions/battles.md` laissait plusieurs points ouverts ; ils ont ete tranches avec
l'utilisateur avant developpement :

- **Bataille nulle** : si la condition ne separe pas les deux Combattants (memes valeurs),
  la carte est defaussee et personne ne marque.
- **Plafond de 7 cartes** : sans plafond, deux Combattants aux caracteristiques identiques
  ne se separeraient jamais. Au-dela de 7 cartes revelees, le joueur ayant remporte le
  plus de batailles remporte le duel ; a egalite, double victoire (les deux infligent
  leurs Degats, conformement a `game.md`). En pratique, ~7 % des duels sont tranches par
  ce plafond.
- **Dos d'une carte multi-caracteristiques** : une couleur unique, choisie parmi celles que
  la condition lit et **figee** par carte (fidele a un jeu physique imprime).
- **Remelange a chaque duel** : les 21 cartes sont remelangees et recoupees en 2 pioches au
  debut de chaque duel. Chaque duel repart du meme ensemble de cartes, et une pioche ne
  peut pas s'epuiser en cours de duel (7 cartes revelees au maximum, 10 par pioche).
- **Ordre des batailles** : en commencant par J1, puis strictement a tour de role — celui
  qui remporte une bataille ne rejoue pas.
- **Choix des Combattants** : J1 engage face visible, J2 choisit ensuite en le connaissant
  (comme `game.md`). J1 est compense par le fait de piocher la premiere carte Bataille.
- **Degats fixes** : le vainqueur inflige exactement ses Degats, que le duel finisse 3-0 ou
  3-2.
- **Equipe visible** : le roster complet des deux joueurs est visible en permanence ; seuls
  le contenu des pioches (hors couleur du dos) reste cache.
- **Capacites** : le systeme decrit par `versions/battles.md` laissait le moment
  d'application ouvert. Les effets qui changent la resolution des batailles (`initiative`,
  `annule_couleur`) sont figes a l'engagement des deux Combattants ; les autres
  s'appliquent a la resolution du duel, modificateurs de Degats d'abord (plancher a 0),
  effets de PV ensuite. Le moteur refuse a l'import toute capacite incoherente avec ce
  decoupage.
- **Initiative contre Initiative** : si les deux Combattants l'ont, elles se neutralisent et
  la bataille reste nulle.
- **« Bataille » = duel** : les conditions `victoire` / `defaite` portent sur le duel, pas
  sur une bataille isolee (c'est le sens de `vengeance` / `confiance` dans
  `versions/battles.md`, qui parlent de « sa bataille lors du duel precedent »).
- **Multiplicateur a 0** : une Capacite « par bataille remportee » sans bataille remportee ne
  produit rien.
- **PV non plafonnes** : un gain de PV peut faire depasser les 10 PV de depart (l'affichage
  le montre en orange) ; les Degats, eux, ne descendent jamais sous 0.
- **Modificateur de Degats sans effet** : `+X Degats` sur un Combattant qui perd son duel
  s'applique bien mais n'est pas rapporte dans le bilan, pour ne pas annoncer des Degats que
  personne n'a subis.
- **Ancien moteur de Pouvoirs retire** : `engine/powers.py` n'existe plus, et le champ
  `pouvoir` de `data/combattants.json` (base sur la Puissance et l'Energie, disparues) a ete
  remplace par `capacite`. `pouvoirs.csv` reste a la racine comme reference du jeu de base.

## Lisibilite de la resolution

Chaque bataille est jouee a l'ecran une par une, meme lorsqu'un seul clic en declenche
deux (celle du joueur puis celle de l'IA) : la carte sort de la pioche choisie en pivotant,
reste un instant face visible, puis file vers le camp qui la remporte (ou grise sur place
si la bataille est nulle), pendant que le marqueur de bataille correspondant s'allume et
que la ligne du rapport de bataille apparait. Le frontend reconstitue l'etat du duel a
chaque etape (score, rapport, dos des pioches tels qu'ils etaient alors) : le resultat du
duel n'est affiche qu'apres la derniere bataille. L'animation est desactivee si le systeme
declare `prefers-reduced-motion`.

Les Capacites sont rendues lisibles de la meme facon : la Capacite de chaque Combattant est
imprimee sur sa carte avec son statut dans le duel en cours (`active`, `inactive`, ou
« selon l'issue » quand elle depend du resultat), une caracteristique ramenee a 0 est
affichee barree de sa valeur imprimee, un bandeau rappelle les Capacites qui agissent
pendant les batailles, les batailles gagnees par l'Initiative sont marquees comme telles
dans le rapport, et le bilan du duel liste chaque Capacite declenchee avec les PV qu'elle a
deplaces. Les statuts sont figes a l'engagement des Combattants : rejouer les batailles a
l'ecran ne devoile jamais l'issue du duel.

## Verifier l'equilibre

```
uv run python generate_metagame.py -n 3000
```

Simule des parties completes IA contre IA (la meme heuristique des deux cotes, equipes
tirees au hasard) et affiche le pourcentage de victoire par Combattant. Sur le roster
fourni, les 22 Combattants tiennent dans une fourchette de 3,5 points (45,5 % a 49,0 % sur
12 000 parties, le solde etant les 5 % de parties nulles).

## Tests effectues

- 30 verifications unitaires du systeme de Capacites (chaque condition, chaque effet,
  chaque multiplicateur, sur des duels rendus deterministes en ne mettant qu'un seul modele
  de carte dans les pioches), rejouees sur 3 graines.
- 2 000 parties completes simulees via le moteur Python (sans crash), avec mesure du
  rythme : 3,65 duels par partie, duels de 3 a 7 cartes (4,7 en moyenne), 14,4 % de
  batailles nulles, 1,9 % des cartes tranchees par l'Initiative, 5,8 % de duels tranches
  par le plafond, 3,1 % de doubles victoires, 50,6 % de parties finies par KO et 5,0 % de
  parties nulles. Les 22 Capacites se declenchent toutes en jeu (1,28 par duel).
- Equilibrage mesure sur les 462 rencontres ordonnees possibles (1 536 duels par
  rencontre, soit 710 000 duels) : ecart maximal entre PV infliges et PV subis de 0,23 PV
  par duel.
- 8 parties completes jouees via l'API HTTP reelle (serveur Flask demarre), verifiant le
  cycle choix du Combattant → batailles alternees → fin de duel (par 3 batailles et par
  plafond) → duel suivant → KO, la coherence des PV a chaque duel (PV de depart + effets de
  Capacite - Degats = PV d'arrivee) et le refus en HTTP 400 des actions invalides.
- Verification visuelle du frontend (ecran de selection avec Capacites et bouton
  « Equipe aleatoire », duel avec une caracteristique annulee, bilan de duel, legendes)
  par captures en navigateur headless.
