# Urban Eredan — Prototype, version duo

Prototype jouable en solo (vs IA) du jeu de societe Urban Eredan, dans sa **version duo** :
chaque bataille engage **deux Combattants de chaque camp**, et la resolution compare les
sommes de Puissance des deux duos.

Les regles appliquees sont celles de `game.md` **telles que modifiees par
`versions/duo.md`** : `game.md` reste la reference du jeu de base, `versions/duo.md` decrit
ce que cette version en change, et ce README documente l'implementation ainsi que les choix
tranches en cours de route.

## Lancer le jeu

Le projet est gere avec [uv](https://docs.astral.sh/uv/). Depuis la racine :

```
uv sync
uv run backend/app.py
```

Puis ouvrir http://127.0.0.1:5000/ dans un navigateur.

Le serveur Flask sert a la fois l'API de jeu (`/api/...`) et les fichiers statiques du
frontend (`frontend/`). Une seule partie est active a la fois (etat en memoire, adapte a un
usage solo local).

## Structure du projet

```
data/combattants.json       Liste des Combattants jouables (editable a la main)
backend/
  app.py                    Serveur Flask (API REST)
  engine/
    models.py               Combattants, Joueurs, legalite des duos
    batailles.py            Catalogue des cartes bataille et deck
    powers.py               Moteur de resolution des Pouvoirs (2 contre 2)
    ia.py                   Heuristique de l'IA (choix du duo + ciblage)
    game.py                 Orchestration d'une Partie (mise en place, batailles, IA)
frontend/
  index.html / style.css / app.js   Interface (100 % cliquable, sans framework)
generate_metagame.py        Simulateur de metagame (equilibrage du roster)
```

## Ce que la version duo change

| | Version de base | Version duo |
|---|---|---|
| Combattants engages | 1 par camp et par duel | **2 par camp et par bataille** |
| Resolution | Puissance contre Puissance | **somme des 2 Puissances** de chaque camp |
| Degats | Degats du vainqueur | **somme des Degats** des 2 vainqueurs |
| Glyphes / Energie | 16 Glyphes, l'Energie active les Pouvoirs | **supprimes** : les Pouvoirs sont toujours actifs |
| PV de depart | 10 | **20** |
| Equipe | 4 Combattants, 1 utilisation chacun | 4 Combattants, **2 utilisations chacun** |
| Choix | J1 choisit, puis J2 | **choix simultane** des deux duos |
| Cartes bataille | aucune | **1 revelee par bataille**, son effet va au vainqueur |

Consequences sur les mots-cles de `pouvoirs.csv` :

- **Supprimes** : le champ `energie_min` et les modificateurs `par_energie`,
  `par_energie_adverse`, `par_energie_en_jeu`, qui n'ont plus de support sans Energie. Les
  valeurs qu'ils multipliaient sont devenues fixes, ou sont passees sur `patience` /
  `impatience` / `premiere_fois` / `seconde_fois` selon la fiche du personnage.
- **Ajoutes** : les conditions `premiere_fois` et `seconde_fois`, satisfaites selon que le
  Combattant est engage pour la premiere ou la seconde fois de la partie.
- **Redefinis** : `courage` / `riposte` ne signifient plus "joue en premier / en second"
  (le choix est simultane) mais "**mon camp resout ses Pouvoirs en premier / en second**".

## Structure d'une bataille

1. La carte bataille du tour est revelee. C'est une information publique : elle fixe l'enjeu
   avant que les duos ne soient choisis.
2. Les deux joueurs verrouillent simultanement leur duo de 2 Combattants distincts.
3. Les deux duos sont reveles.
4. Chaque joueur designe la cible des Pouvoirs a cible unique de son duo.
5. Les Pouvoirs sont resolus (camp J1 puis camp J2), les sommes de Puissance comparees.
6. Le camp vainqueur inflige la somme des Degats de ses 2 Combattants.
7. Le ou les vainqueurs appliquent l'effet de la carte bataille.

Le vainqueur d'une bataille est le camp J1 de la suivante ; en cas de double victoire, J1 et
J2 s'echangent.

## Cartes bataille

Un exemplaire de chaque carte, melange en debut de partie ; une carte revelee par bataille,
soit 4 cartes vues par partie sur les 7 possibles. L'effet est applique par le vainqueur (par
les deux camps en cas de double victoire, ce qui rend les effets d'information reciproques).

| Carte | Effet | Quand |
|---|---|---|
| Butin | Le vainqueur gagne 2 PV | apres les Degats |
| Acharnement | Les Degats infliges par le vainqueur sont augmentes de 2 | pendant la bataille |
| Reperage | A la bataille suivante, l'adversaire verrouille son duo en premier et en revele 1 Combattant tire au hasard | bataille suivante |
| Intimidation | Idem, mais l'adversaire revele son duo entier | bataille suivante |
| Second souffle | Les 2 Combattants du duo vainqueur recuperent l'utilisation depensee pour cette bataille | apres les Degats |
| Ovation | Le vainqueur gagne 1 PV par Combattant de son duo engage pour la premiere fois | apres les Degats |
| Escarmouche | Aucun effet : seuls les Degats comptent | — |

## Les 2 utilisations par Combattant

Chaque Combattant ne peut etre engage que 2 fois sur la partie (les ronds sous sa carte les
comptent, equivalent de la carte inclinee du jeu physique). Avec 4 Combattants a 2
utilisations pour 4 batailles de 2 places, **toutes les utilisations sont consommees** : la
composition n'est pas un choix, seul l'ordre d'engagement en est un (et donc le moment ou se
declenchent `premiere_fois` et `seconde_fois`). `Second souffle` est la seule carte qui rend
la composition reellement libre, en ajoutant deux utilisations.

Cette exactitude cree un piege que le moteur ferme : un joueur peut se bloquer tout seul.
Jouer `{A,B}` puis `{A,C}` puis `{B,C}` laisserait D seul avec 2 utilisations pour la
derniere bataille, qui exige 2 Combattants distincts. `Joueur.duos_legaux()` n'expose donc
que les duos qui preservent la faisabilite du calendrier — un Combattant ne doit jamais
pouvoir remplir plus de places qu'il ne reste de batailles (`models.calendrier_faisable`).
Les duos exclus sont grises dans l'interface.

## Schema des Combattants

`data/combattants.json` peut etre modifie a la main puis rechargé automatiquement au
lancement d'une nouvelle partie (pas besoin de redemarrer le serveur). Chaque Combattant ne
possede qu'un seul Pouvoir, toujours actif :

```json
{
  "id": "identifiant_unique",
  "nom": "Nom affiche",
  "puissance": 4,
  "degats": 3,
  "pouvoir": {
    "description": "Texte affiche sur la carte",
    "condition": null,
    "modificateur": null,
    "effets": [ { "type": "puissance", "cible": "soi", "valeur": 2 } ]
  }
}
```

- `condition` (optionnel) : `courage`, `riposte`, `vengeance`, `domination`,
  `premiere_fois`, `seconde_fois`, `victoire`, `defaite`, `surpuissance`.
- `modificateur` (optionnel) : `patience`, `impatience`, `contrecoup`.
- `effets` : liste d'effets, chacun avec un `type` :
  - `puissance` / `degats` : `cible` (`soi` ou `adversaire`) et `valeur` (entier signe).
  - `vie` : `cible` et `valeur`. Modifie les PV d'un **joueur**, pas une statistique de
    Combattant : ne demande donc aucun ciblage.
  - `stop_pouvoir`, `copie_pouvoir`, `echange` : aucun champ supplementaire, visent le
    Combattant adverse designe.
  - `protection` : aucun champ supplementaire.
  - `vampirisme` : `valeur` = X (reduit les PV adverses de X, gagne X PV).

Le texte `description` est affiche tel quel sur la carte : les nombres qu'il contient doivent
correspondre aux `valeur` des effets.

## Ciblage : un effet a cible unique, deux adversaires

Un Pouvoir qui porte au moins un effet a cible unique (Puissance ou Degats **adverses**,
`stop_pouvoir`, `copie_pouvoir`, `echange`) oblige son proprietaire a designer **l'un des 2
Combattants adverses**. Le choix appartient au joueur, et il a lieu **apres revelation des
deux duos** : designer a l'aveugle n'aurait aucun sens puisque le duo adverse est inconnu au
moment du verrouillage. Un Pouvoir ne designe qu'une seule cible, meme s'il porte plusieurs
effets a cible unique (Nova cible ainsi le meme Combattant pour sa copie et pour son
annulation).

## Hypotheses et choix d'implementation

- **Ordre de resolution** : les camps conservent un role J1 / J2 (le vainqueur de la bataille
  precedente est J1). Le camp J1 resout les Pouvoirs de ses 2 Combattants, dans l'ordre du
  duo, avant le camp J2. Cet ordre reste necessaire des que deux `stop_pouvoir` ou deux
  `echange` se croisent.
- **Egalite des sommes de Puissance** : double victoire. Les deux camps encaissent les Degats
  de l'autre et appliquent l'effet de la carte bataille, et J1 / J2 s'echangent au tour
  suivant, conformement a `game.md`.
- **`protection` protege le CAMP entier** de son porteur (ses 2 Combattants et les PV de son
  joueur) : elle annule les modifications adverses deja subies et bloque les suivantes. Sans
  cela, l'adversaire se contenterait de designer l'autre Combattant du duo et la Protection
  ne vaudrait rien. Elle ne bloque pas les Degats de fin de bataille, qui relevent de la
  regle de base et non d'un Pouvoir.
- **`surpuissance` se compare sur les sommes figees** au moment de la determination du
  vainqueur, pour qu'un Pouvoir de la passe differee ne puisse pas reecrire a posteriori le
  critere qui l'a declenche.
- **`contrecoup` retourne sur son porteur** l'effet normalement dirige vers l'adversaire, et
  uniquement si son camp remporte la bataille (conforme a `pouvoirs.csv`). L'implementation de
  la version de base omettait cette redirection : Cascade soignait donc son adversaire.
- **`copie_pouvoir`** copie la definition du Pouvoir du Combattant designe et l'execute du
  point de vue du copieur ; les effets a cible unique du Pouvoir copie visent la meme cible.
  Limitations POC inchangees : copier un Pouvoir conditionne par l'issue de la bataille
  (`victoire` / `defaite` / `surpuissance` / `contrecoup`) n'est pas supporte, ni copier un
  Pouvoir qui copie lui-meme un Pouvoir (recursion infinie), ni copier un Pouvoir deja annule.
- **Choix simultane face a une IA** : l'IA verrouille son duo a l'ouverture de la bataille,
  donc a l'aveugle. Seules les cartes `Reperage` et `Intimidation` inversent cet ordre, en
  obligeant leur victime a s'engager la premiere et a en reveler tout ou partie. Si les deux
  camps ont gagne une telle carte (double victoire), l'IA choisit malgre tout a l'aveugle :
  son devoir de revelation est deja rempli par le fait qu'elle s'engage sans rien savoir.
- **`surpuissance` est mort en duo** : la condition exige le double de la Puissance adverse,
  ce qui, sur des sommes de deux Combattants, ne se produit jamais (0 % de declenchement
  mesure sur 8 000 parties). Le seul Combattant qui la portait, Gambit, a vu sa condition
  basculer sur le modificateur `patience` en gardant son identite (`+Vie` / `-Vie adverse`).
  Le mot-cle reste implemente pour un futur personnage.
- **Equipe visible** : le roster complet de chaque joueur est visible par l'autre pendant
  toute la partie, ainsi que le compteur d'utilisations de chaque Combattant. Seul le duo
  engage par l'IA reste cache jusqu'a la revelation.

## IA

`engine/ia.py` choisit, parmi les duos legaux, celui qui maximise une estimation de la
Puissance totale du duo (puis les Degats, puis la Vie). Cette estimation ne compte que ce qui
est certain au moment du choix :

- `courage` / `riposte` (le role du camp est connu avant le choix), `vengeance` / `domination`
  (PV courants) et `premiere_fois` / `seconde_fois` (compteur d'utilisations) sont evalues
  immediatement ; `victoire` / `defaite` / `surpuissance` et `contrecoup` dependent de l'issue
  de la bataille et ne sont jamais comptes.
- `patience` / `impatience` sont calcules directement.
- `stop_pouvoir` / `copie_pouvoir` / `protection` / `echange` dependent du duo adverse,
  inconnu au moment du choix : ils ne modifient pas le score.

Quand `Reperage` ou `Intimidation` lui a revele tout ou partie du duo adverse, l'IA ne cherche
plus le maximum mais **gagne au meilleur prix** : elle engage le duo legal le moins fort qui
batte encore l'estimation adverse, et si aucun ne le peut, elle sacrifie la bataille avec son
duo le plus faible pour preserver ses Combattants forts. C'est aussi ce qui donne sa valeur a
un Pouvoir conditionne par `defaite`.

Pour le ciblage (`choisir_cible`), la regle depend de l'effet dominant : `echange` vise le
plus fort (c'est ce qu'on recupere), `copie_pouvoir` le Pouvoir copiable le plus utile,
`stop_pouvoir` le plus menacant, un malus le Combattant de plus forte Puissance.

## Equilibrage

`generate_metagame.py` simule des parties IA contre IA et mesure, pour chaque Combattant, le
**pourcentage de parties gagnees par les equipes dont il fait partie** — et non son taux de
victoire en bataille, conformement a `versions/duo.md`. Un Combattant compte comme gagnant des
lors que son equipe gagne, meme s'il a perdu ses propres batailles, ce qui rend viables les
Combattants qui ont interet a perdre.

```
uv run generate_metagame.py -n 10000
```

Etat du roster : sur des echantillons independants de 60 000 parties, les 22 Combattants
tiennent dans une bande d'environ **44,8 % a 53,2 %**, de moyenne 47,8 %. Un ou deux
Combattants du bas de tableau frolent la borne des 45 % selon l'echantillon, a moins d'un
point et dans l'intervalle de confiance de la mesure (+/- 0,7 pt a 60 000 parties).

**La bande 45-55 % est legerement mal centree pour cette version**, et c'est structurel :
environ 4,3 % des parties se terminent par une egalite, comptee comme une defaite des deux
cotes, ce qui verrouille la moyenne des taux de victoire a `(1 - 0,043) x 50 = 47,8 %`. Aucun
reglage ne peut deplacer cette moyenne. La bande laisse donc 2,8 points de marge sous la
moyenne contre 7,2 au-dessus : y faire tenir 22 Combattants exigerait de resserrer l'ecart a
moins de 5,6 points, ce que la granularite du levier de Puissance (7 pt par point) ne permet
pas. Une bande symetrique autour de la moyenne reelle, soit environ **43-53 %**, decrirait
mieux l'equilibre atteignable ; sinon, departager les egalites ramenerait la moyenne vers
50 % (`game.md` n'en prevoit pas et ce prototype n'en invente pas).

Trois taux de change mesures sur ce roster, utiles pour tout reglage futur :

- **1 point de Puissance ≈ 7 pt** de taux de victoire. Comme aucun Combattant ne peut etre
  mis au banc (toutes les utilisations sont consommees), sa Puissance de base pese
  directement, et c'est un levier grossier : pour certains personnages, aucune valeur entiere
  ne donne exactement 50 %.
- **1 point de Degats ≈ 2,7 pt**, le levier fin.
- **1 PV apporte par un Pouvoir ≈ 1,2 pt**. Remporter une bataille valant environ 12 PV
  d'ecart, les effets `vie` calibres pour la version de base etaient tres sous-evalues en duo
  et ont ete releves.

Corollaire pratique : **compare un nouveau Combattant a la moyenne de 47,8 %, pas a 50 %**.
Viser 50 % pour tout le monde pousse a gonfler indefiniment le roster sans jamais reduire
l'ecart, et le critere etant relatif, renforcer un Combattant affaiblit tous les autres.

## Tests effectues

- **Invariants de regles** sur 2 000 parties simulees : aucun Combattant ne depasse 2
  utilisations, un duo legal existe toujours, les duos comportent 2 Combattants distincts et
  disponibles, la partie ne depasse jamais 4 batailles, les 7 cartes bataille apparaissent.
- **Calibrage des PV** sur 3 000 parties menees jusqu'a la 4e bataille (PV eleves pour eviter
  tout KO) : le camp le plus touche encaisse 18,9 degats en moyenne sur la partie. A 20 PV,
  42 % des parties finissent par KO et 64 % descendent a 3 PV ou moins.
- **API HTTP reelle** (serveur Flask demarre) : 12 parties completes jouees de bout en bout,
  verification de la forme de chaque reponse consommee par le frontend, des trois phases
  (`choix_duo`, `ciblage`, `bataille_resolue`), de la coherence des sommes de Puissance, et du
  rejet propre (HTTP 400) des actions invalides (equipe incomplete ou avec doublon, duo avec
  doublon, Combattant hors equipe, ciblage hors phase).
- **Frontend pilote dans un navigateur headless** (Chromium) : parcours complet au clic
  (selection des 4 Combattants → lancement → choix du duo → ciblage → resultat) sans aucune
  erreur JavaScript, avec verification du rendu des 20 ronds de PV, des 8 ronds
  d'utilisation, de la carte bataille, du panneau de ciblage et du panneau du camp vainqueur.
- **Equilibrage** verifie sur deux echantillons de 60 000 parties independants du reglage,
  et taux de change (Puissance / Degats / PV) mesures separement pour outiller les
  reglages futurs.
