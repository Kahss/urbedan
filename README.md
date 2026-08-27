# Urban Eredan — Prototype (version « cartes Bataille »)

Prototype jouable en solo (vs IA) du jeu de societe Urban Eredan (`game.md`), dans la
variante decrite par `versions/battles.md` : un duel ne se resout plus par une comparaison
de Puissance, mais en remportant **3 batailles** revelees automatiquement, une par une,
depuis une pioche commune. Backend Python (moteur de regles + IA), frontend web
(HTML/CSS/JS, jouable uniquement au clic).

## Ce qui change par rapport a la version de reference

- Les cartes **Glyphes** et l'**Energie** disparaissent ; les Pouvoirs sont remplaces par
  un systeme de **Capacites** (une par Combattant, cf. plus bas).
- Un Combattant n'a plus de Puissance : il porte trois caracteristiques, **Force**
  (rouge), **Dexterite** (vert) et **Sagesse** (bleu), chacune de 0 a 7, plus ses Degats
  et sa Capacite.
- Un deck de **15 cartes Bataille** forme une **pioche unique et persistante pour toute la
  partie**, posee au centre de la table : elle n'est remelangee que lorsqu'elle est
  epuisee. Chaque carte porte la condition qui designe le vainqueur de la bataille ; aucune
  information n'est visible avant qu'une carte ne soit revelee (pioche a l'aveugle, sans
  choix). Un compteur a l'ecran suit, par couleur, combien de cartes sont deja sorties
  depuis le dernier remelange.
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
    batailles.py            Les 15 cartes Bataille, leur resolution et la pioche
    capacites.py            Le vocabulaire des Capacites (condition / effet / multiplicateur)
    models.py               Combattants, Joueurs
    ia.py                   Heuristique de l'IA (choix du Combattant)
    game.py                 Orchestration d'une Partie (mise en place, duels, batailles)
frontend/
  index.html / style.css / app.js   Interface (100% cliquable, sans framework)
generate_metagame.py        Simulation IA contre IA : % de victoire par Combattant
```

## Les 15 cartes Bataille

Definies dans `backend/engine/batailles.py` (`MODELES`), avec leur nom, leur condition et
leur couleur (visible seulement une fois la carte revelee). Le deck est structure de facon
symetrique : chaque caracteristique est la caracteristique principale de 4 cartes, et les
3 dernieres cartes, grises, lisent les trois caracteristiques.

| Type de condition | Exemplaires | Exemple |
| --- | --- | --- |
| `max` : la caracteristique la plus haute l'emporte | 3 par caracteristique | Bras de fer — Force la plus haute |
| `somme` : la somme de deux caracteristiques la plus haute | 1 par caracteristique | Escalade sauvage — Force + Dexterite la plus haute |
| `total` : le total des trois le plus haut | 1 | Melee generale |
| `meilleure` : la meilleure des trois la plus haute | 1 | Coup d'eclat |
| `pire` : celui dont la plus petite des trois est la plus faible **perd** | 1 | Maillon faible |

Les caracteristiques tournent en cycle (Force → Dexterite → Sagesse → Force) pour les
sommes, de sorte que les trois groupes de 4 cartes soient rigoureusement equivalents :
aucune caracteristique n'est structurellement meilleure qu'une autre.

**Aucune information** n'est disponible avant qu'une carte ne soit revelee : la pioche se
fait entierement a l'aveugle, il n'y a plus de choix a faire. La couleur d'une carte
(rouge/vert/bleu pour les 4 cartes de chaque caracteristique, gris pour les 3 cartes
globales) n'est affichee qu'apres reveal, et sert au compteur de cartes sorties.

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
| Nova | 0 / 1 / 7 | 8 | 3 | Annule la Sagesse adverse |
| Grind | 4 / 5 / 1 | 10 | 2 | Confiance : +2 Degats |
| Blaze | 4 / 3 / 2 | 9 | 3 | Vengeance : +3 Degats |
| Iron | 7 / 0 / 2 | 9 | 3 | -2 Degats adverses |
| Cobra | 1 / 7 / 0 | 8 | 5 | Confiance : Vampirisme 1 |
| Echo | 1 / 5 / 4 | 10 | 2 | Initiative |
| Vex | 0 / 1 / 7 | 8 | 4 | Defaite : -2 PV adverses |
| Mirage | 2 / 2 / 4 | 8 | 4 | Second : Annule la Dexterite adverse |
| Surge | 3 / 2 / 3 | 8 | 5 | +1 Degat par duel joue |
| Jab | 5 / 4 / 0 | 9 | 4 | Second : +3 Degats |
| Buzzer | 1 / 4 / 4 | 9 | 2 | -1 PV adverse par bataille remportee |
| Verve | 0 / 3 / 5 | 8 | 5 | Victoire : +3 PV |
| Gambit | 3 / 0 / 5 | 8 | 3 | +1 PV par bataille remportee |
| Nitro | 3 / 5 / 0 | 8 | 5 | +1 Degat par duel restant |
| Cascade | 5 / 3 / 1 | 9 | 3 | Defaite : +2 PV |
| Mime | 3 / 4 / 2 | 9 | 2 | Annule la Force adverse |
| Verrou | 7 / 0 / 2 | 9 | 2 | -1 Degat adverse par bataille perdue |
| Furet | 1 / 5 / 2 | 8 | 5 | Victoire : Vampirisme 1 |
| Suture | 0 / 2 / 7 | 9 | 2 | Defaite : +1 PV par duel joue |
| Toph | 5 / 1 / 3 | 9 | 4 | Vengeance : Initiative |
| Loup | 5 / 1 / 2 | 8 | 3 | Victoire : Vampirisme 2 |

Une Capacite est un cout comme un autre : elle se paie sur les caracteristiques et les
Degats. `Annule une couleur` est ainsi le contrepoids des profils extremes que le deck
favorise — un 7 (le maximum) remporte trois cartes de sa couleur, mais tombe a 0 devant
Nova, Mirage ou Mime.

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

- `force` / `dexterite` / `sagesse` : entiers de 0 a 7 (le moteur refuse toute valeur hors
  de cet intervalle au chargement).
- `degats` : PV retires a l'adversaire quand le Combattant remporte son duel.
- `capacite` : `condition` et `multiplicateur` peuvent valoir `null` ; `effet` est
  obligatoire et porte un `type`, une `valeur` entiere (sauf `initiative`) et, pour
  `annule_couleur`, une `couleur` (`rouge`, `vert` ou `bleu`). Le libelle imprime sur la
  carte est genere a partir de ces trois champs : il ne peut pas mentir sur l'effet reel.

### Equilibrer un Combattant

Trois leviers se compensent : les **caracteristiques** (0 a 7 chacune) et la **Capacite**
determinent la frequence a laquelle un Combattant gagne ses duels, les **Degats** paient
cette frequence. Le roster fourni se tient generalement entre 8 et 10 de total : en
dessous, un Combattant perd trop souvent pour que ses Degats (plafonnes a 5) puissent
compenser — sauf s'il s'agit justement d'un profil **situationnel** (cf. plus bas), qui ne
tire pas sa valeur de son propre taux de victoire. Trois proprietes guident la
repartition :

- **Les valeurs extremes valent mieux que les valeurs moyennes** : un 7 (le maximum)
  remporte les 3 cartes « la plus haute » de sa couleur, et un 0 remporte celle « la plus
  basse » — au prix de `Maillon faible`, qui fait perdre la bataille a celui dont la plus
  petite caracteristique est la plus faible, et au prix des Capacites `annule_couleur`, qui
  font tomber une caracteristique a 0.
- **Un total eleve, ou une Capacite forte, doit se payer en Degats** — sauf pour un profil
  situationnel, qui n'a pas vocation a gagner ses duels (voir ci-dessous).
- **Une Capacite multipliee coute cher** : `patience` et `impatience` valent 2,5 fois
  l'effet en moyenne, `par bataille remportee`/`perdue` environ 1,5 fois. Reservez-les aux
  profils fragiles, qui ont de la marge sur leurs Degats pour les payer.

**Personnages situationnels.** Un Combattant peut ne pas etre concu pour gagner ses propres
duels : une Capacite conditionnee par `defaite`, ou qui reduit les Degats ou une
caracteristique de l'adversaire (`degats_adverse`, `annule_couleur`), rapporte a l'equipe
meme quand le Combattant perd. Iron, Vex, Verrou et Suture, par exemple, tirent leur poids
d'un effet qui ne depend pas d'une victoire personnelle — leur total de caracteristiques ou
leur taux de victoire en duel n'a donc pas a etre remonte vers la moyenne.

L'equilibrage se juge desormais sur le **taux de victoire des equipes** dont un Combattant
a fait partie (mesure par `generate_metagame.py`, cf. section suivante), pas sur son propre
taux de victoire en duel : la fourchette cible est **40 % a 60 %**, volontairement large
pour laisser leur place aux profils situationnels ci-dessus.

*Note historique* : le roster (avant l'introduction du plafond a 7 caracteristiques et de
la fourchette elargie a 40-60 %) avait ete regle sur un plafond de 5 par caracteristique et
une fourchette cible de 45-55 % : chaque Combattant infligeait alors en moyenne autant de
PV qu'il en subissait, a **0,23 PV par duel** pres (mesure sur les 462 rencontres ordonnees
possibles), et les Combattants gagnaient de 36 % a 79 % de leurs propres duels — deja a
l'epoque, c'etait le prix paye en Degats qui remettait tout le monde a egalite au niveau de
l'equipe, pas le taux de victoire individuel en duel. Ces chiffres n'ont pas ete
recalcules depuis les retouches de roster ci-dessus.

## IA

`engine/ia.py` :

- **Choix du Combattant** : tire au hasard parmi ceux qui n'ont pas encore combattu ;
  l'IA ne contre-choisit pas le Combattant adverse.

La revelation des cartes Bataille est automatique et ne laisse plus de decision a prendre,
ni pour l'IA ni pour le joueur humain : la pioche se fait entierement a l'aveugle. Le
joueur humain dispose neanmoins d'une information publique : le deck est liste sur l'ecran
de selection, et le compteur de couleurs affiche, pendant le duel, combien de cartes de
chaque couleur sont deja sorties.

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
- **Pioche unique et persistante** : les 15 cartes forment une seule pioche, commune aux
  deux joueurs, qui n'est remelangee que lorsqu'elle est epuisee et qu'il faut encore
  piocher — jamais systematiquement entre deux duels. Le plafond de 7 cartes par duel reste
  bien en dessous des 15 cartes du deck : un duel ne peut donc jamais a lui seul epuiser la
  pioche plus d'une fois.
- **Choix des Combattants** : J1 engage face visible, J2 choisit ensuite en le connaissant
  (comme `game.md`).
- **Degats fixes** : le vainqueur inflige exactement ses Degats, que le duel finisse 3-0 ou
  3-2.
- **Equipe visible** : le roster complet des deux joueurs est visible en permanence ; seul
  l'ordre des cartes dans la pioche reste cache.
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

Chaque bataille est jouee a l'ecran une par une : un clic sur la pioche revele la carte,
qui pivote, reste un instant face visible, puis file vers le camp qui la remporte (ou
grise sur place si la bataille est nulle), pendant que le marqueur de bataille
correspondant s'allume et que la ligne du rapport de bataille apparait. Le frontend
reconstitue l'etat du duel a chaque etape (score, rapport, cartes restantes et compteur de
couleurs tels qu'ils etaient alors) : le resultat du duel n'est affiche qu'apres la
derniere bataille. L'animation est desactivee si le systeme declare
`prefers-reduced-motion`.

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
tirees au hasard) et affiche, pour chaque Combattant, le pourcentage de parties gagnees par
les equipes dont il a fait partie (pas son taux de victoire en duel, cf. « Equilibrer un
Combattant » ci-dessus) — c'est ce pourcentage qui doit rester dans la fourchette cible de
**40 % a 60 %**. Sur une version anterieure du roster (plafond de 5 par caracteristique,
fourchette cible 45-55 %), les 22 Combattants tenaient dans une fourchette de 3,5 points
(45,5 % a 49,0 % sur 12 000 parties, le solde etant les 5 % de parties nulles) ; ce chiffre
n'a pas ete recalcule depuis.

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
