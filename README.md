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
    ia.py                   Heuristique de l'IA (duo, ciblage, revelation, recharge)
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
  Combattant est engage pour la premiere ou la seconde fois de la partie, et trois
  conditions a seuil qui lisent le duo en presence : `puissance_alliee` (le coequipier),
  `puissance_base_adverse` et `degats_base_adverse` (au moins un des 2 Combattants d'en
  face). Le seuil est porte par le champ `seuil` du Pouvoir.
- **Elargi** : un malus de `degats` dirige vers l'adversaire ne frappe plus un Combattant
  mais le **total des Degats du duo adverse** — c'est le duo entier qui inflige ses Degats,
  c'est le duo entier qu'on affaiblit. Un total ne descend jamais sous 0.
- **Redefinis** : `courage` / `riposte` ne signifient plus "joue en premier / en second"
  (le choix est simultane) mais "**mon camp resout ses Pouvoirs en premier / en second**".

## Structure d'une bataille

1. La carte bataille du tour est revelee. C'est une information publique : elle fixe l'enjeu
   avant que les duos ne soient choisis.
2. Les deux joueurs verrouillent simultanement leur duo de 2 Combattants distincts. Un
   `Reperage` gagne au tour precedent brise cette simultaneite : sa victime s'engage la
   premiere et revele celui de ses 2 Combattants qu'elle choisit.
3. Les deux duos sont reveles.
4. Chaque joueur designe la cible des Pouvoirs a cible unique de son duo, s'il en a.
5. Les Pouvoirs sont resolus (camp J1 puis camp J2), les sommes de Puissance comparees.
6. Le camp vainqueur inflige la somme des Degats de ses 2 Combattants, diminuee des malus
   de Degats adverses et jamais negative.
7. Le ou les vainqueurs appliquent l'effet de la carte bataille. `Second souffle` demande
   au vainqueur un dernier choix : a quel Combattant de son equipe rendre une utilisation.

Le vainqueur d'une bataille est le camp J1 de la suivante ; en cas de double victoire, J1 et
J2 s'echangent.

## Cartes bataille

Un exemplaire de chaque carte, melange en debut de partie ; une carte revelee par bataille,
soit 4 cartes vues par partie sur les 7 possibles. L'effet est applique par le vainqueur (par
les deux camps en cas de double victoire, ce qui rend les effets d'information reciproques).

| Carte | Effet | Quand |
|---|---|---|
| À la loyale | Aucun effet : seuls les Degats comptent | — |
| Dans les bas-fonds | Les Degats infliges par le vainqueur sont augmentes de 2 | pendant la bataille |
| Soigner les blessés | Le vainqueur gagne 2 PV | apres les Degats |
| Planification | Patience : le vainqueur gagne 1 PV par bataille jouee, celle-ci comprise | apres les Degats |
| Second souffle | Le vainqueur rend une utilisation au Combattant de son equipe qu'il choisit | apres les Degats |
| Repérage | A la bataille suivante, l'adversaire verrouille son duo en premier et revele celui de ses 2 Combattants qu'il choisit | bataille suivante |
| Dépasser ses limites | A la bataille suivante, toutes les conditions des Pouvoirs du vainqueur sont considerees validees | bataille suivante |

Deux cartes demandent un choix a leur beneficiaire, materialise par un panneau de boutons :
`Second souffle` (quel Combattant recharger, apres la resolution) et `Repérage` (quel
Combattant montrer, cote victime, apres le verrouillage de son duo). `Repérage` laisse donc
le choix a celui qui **subit** la carte : il montre ce qu'il veut bien montrer, et l'IA
revele systematiquement son Combattant de plus faible Puissance pour faire sous-estimer son
duo.

`Dépasser ses limites` valide **toutes** les conditions du vainqueur au tour suivant, y
compris `victoire` et `defaite` en meme temps : un Clerc y encaisse ses +3 PV de defaite
tout en gagnant sa bataille.

## Les 2 utilisations par Combattant

Chaque Combattant ne peut etre engage que 2 fois sur la partie (les ronds sous sa carte les
comptent, equivalent de la carte inclinee du jeu physique). Avec 4 Combattants a 2
utilisations pour 4 batailles de 2 places, **toutes les utilisations sont consommees** : la
composition n'est pas un choix, seul l'ordre d'engagement en est un (et donc le moment ou se
declenchent `premiere_fois` et `seconde_fois`). `Second souffle` est la seule carte qui
desserre cet etau, en rendant une utilisation au Combattant de son choix — un Combattant
epuise redevient jouable, et peut donc etre engage trois fois dans la partie.

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
    "seuil": null,
    "modificateur": null,
    "effets": [ { "type": "puissance", "cible": "soi", "valeur": 2 } ]
  }
}
```

- `condition` (optionnel) : `courage`, `riposte`, `vengeance`, `domination`,
  `premiere_fois`, `seconde_fois`, `victoire`, `defaite`, `surpuissance`, plus trois
  conditions a seuil qui exigent un champ `seuil` a cote de `condition` :
  - `puissance_alliee` : le coequipier du duo a au moins `seuil` de Puissance de base.
  - `puissance_base_adverse` / `degats_base_adverse` : au moins un des 2 Combattants
    adverses a au moins `seuil` de Puissance / de Degats de base.
  Ces trois conditions se lisent sur les caracteristiques **de base**, celles imprimees sur
  la carte : sans cela le resultat dependrait de l'ordre de resolution des deux camps.
- `modificateur` (optionnel) : `patience`, `impatience`, `contrecoup`.
- `effets` : liste d'effets, chacun avec un `type` :
  - `puissance` : `cible` (`soi` ou `adversaire`) et `valeur` (entier signe). Vers
    l'adversaire, vise le Combattant designe.
  - `degats` : `cible` et `valeur`. Vers `soi`, modifie les Degats du Combattant ; vers
    `adversaire`, retranche du **total du duo adverse** (aucun ciblage, plancher a 0).
  - `vie` : `cible` et `valeur`. Modifie les PV d'un **joueur**, pas une statistique de
    Combattant : ne demande donc aucun ciblage.
  - `stop_pouvoir`, `copie_pouvoir`, `echange` : aucun champ supplementaire, visent le
    Combattant adverse designe.
  - `protection` : aucun champ supplementaire.
  - `vampirisme` : `valeur` = X (reduit les PV adverses de X, gagne X PV).

Le texte `description` est affiche tel quel sur la carte : les nombres qu'il contient doivent
correspondre aux `valeur` des effets.

## Ciblage : un effet a cible unique, deux adversaires

Un Pouvoir qui porte au moins un effet a cible unique (Puissance **adverse**,
`stop_pouvoir`, `copie_pouvoir`, `echange`) oblige son proprietaire a designer **l'un des 2
Combattants adverses**. Le choix appartient au joueur, et il a lieu **apres revelation des
deux duos** : designer a l'aveugle n'aurait aucun sens puisque le duo adverse est inconnu au
moment du verrouillage. Un Pouvoir ne designe qu'une seule cible, meme s'il porte plusieurs
effets a cible unique.

Un malus de Degats adverse ne compte **pas** parmi eux : il porte sur le total du duo d'en
face. Aucun Combattant du roster actuel ne requiert donc de ciblage, et la phase
correspondante ne se declenche jamais en pratique — les mots-cles restent implementes et
testes pour les Combattants a venir.

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
  uniquement si son camp remporte la bataille (conforme a `pouvoirs.csv`). C'est ce qui fait
  du Barbare un Combattant qui paie ses victoires : son `-2 PV` s'applique a lui, et
  seulement quand son duo l'emporte.
- **`copie_pouvoir`** copie la definition du Pouvoir du Combattant designe et l'execute du
  point de vue du copieur ; les effets a cible unique du Pouvoir copie visent la meme cible.
  Limitations POC inchangees : copier un Pouvoir conditionne par l'issue de la bataille
  (`victoire` / `defaite` / `surpuissance` / `contrecoup`) n'est pas supporte, ni copier un
  Pouvoir qui copie lui-meme un Pouvoir (recursion infinie), ni copier un Pouvoir deja annule.
- **Choix simultane face a une IA** : l'IA verrouille son duo a l'ouverture de la bataille,
  donc a l'aveugle. Seule la carte `Reperage` inverse cet ordre, en obligeant sa victime a
  s'engager la premiere et a montrer l'un de ses 2 Combattants. Si les deux camps l'ont
  gagnee (double victoire), l'IA choisit malgre tout a l'aveugle : son devoir de revelation
  est deja rempli par le fait qu'elle s'engage sans rien savoir.
- **Malus de Degats au niveau du duo** : un `degats` adverse est applique au camp d'en face
  (`CampBataille.bonus_degats`), pas a un Combattant, et le total inflige est ramene a 0 s'il
  passe en negatif. Le plancher apparait explicitement dans le detail affiche, pour que la
  somme lue par le joueur reste exacte.
- **`Depasser ses limites`** pose `CampBataille.conditions_forcees`, teste en tete de
  `_verifier_condition` : toutes les conditions du camp sont alors vraies, `victoire` et
  `defaite` comprises, donc simultanement. Les Pouvoirs concernes restent resolus a leur
  passe habituelle (immediate ou differee) : la carte change ce qui se declenche, pas quand.
- **`surpuissance` est mort en duo** : la condition exige le double de la Puissance adverse,
  ce qui, sur des sommes de deux Combattants, ne se produit jamais. Aucun Combattant du
  roster ne la porte ; le mot-cle reste implemente pour un futur personnage, comme
  `protection`, `stop_pouvoir`, `copie_pouvoir`, `echange`, `impatience`, `courage`,
  `riposte` et `premiere_fois`, aujourd'hui sans porteur.
- **Equipe visible** : le roster complet de chaque joueur est visible par l'autre pendant
  toute la partie, ainsi que le compteur d'utilisations de chaque Combattant. Seul le duo
  engage par l'IA reste cache jusqu'a la revelation.

## IA

`engine/ia.py` choisit, parmi les duos legaux, celui qui maximise une estimation de la
Puissance totale du duo (puis les Degats, puis la Vie). Cette estimation ne compte que ce qui
est certain au moment du choix :

- `courage` / `riposte` (le role du camp est connu avant le choix), `vengeance` / `domination`
  (PV courants), `premiere_fois` / `seconde_fois` (compteur d'utilisations) et
  `puissance_alliee` (le coequipier fait partie du duo evalue) sont evalues immediatement ;
  `victoire` / `defaite` / `surpuissance` et `contrecoup` dependent de l'issue de la bataille,
  `puissance_base_adverse` / `degats_base_adverse` du duo d'en face : ils ne sont jamais
  comptes. Un `Depasser ses limites` gagne au tour precedent fait au contraire compter
  toutes les conditions comme acquises.
- `patience` / `impatience` sont calcules directement.
- `stop_pouvoir` / `copie_pouvoir` / `protection` / `echange` dependent du duo adverse,
  inconnu au moment du choix : ils ne modifient pas le score.

Quand `Reperage` lui a revele un Combattant du duo adverse, l'IA ne cherche plus le maximum
mais **gagne au meilleur prix** : elle engage le duo legal le moins fort qui batte encore
l'estimation adverse, et si aucun ne le peut, elle sacrifie la bataille avec son duo le plus
faible pour preserver ses Combattants forts. C'est aussi ce qui donne sa valeur a un Pouvoir
conditionne par `defaite`.

Les deux choix demandes par les cartes bataille suivent la meme logique d'information :
`choisir_revelation` montre le Combattant de plus faible Puissance (l'adversaire estime le
duo sur ce qu'il voit, autant le faire sous-estimer), `choisir_second_souffle` recharge le
Combattant le plus fort parmi ceux ayant deja depense une utilisation — seuls ceux-la en
gagnent reellement une.

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

**Etat mesure du roster actuel** (40 000 parties, IA contre IA, marge d'environ +/- 0,9 pt) :

| Combattant | P / D | Pouvoir | % parties gagnees |
|---|---|---|---|
| Paladin | 4 / 3 | Vengeance : +2 Puissance, +2 Degats | 79,0 % |
| Sorcier | 4 / 2 | Victoire : Vampirisme 2 | 68,8 % |
| Barbare | 4 / 6 | Contrecoup : -2 PV | 63,5 % |
| Moine | 3 / 2 | Patience : +1 Degat | 50,6 % |
| Mage | 3 / 2 | -2 Degats au duo adverse | 49,7 % |
| Guerrier | 3 / 4 | Aucun effet | 49,5 % |
| Druide | 1 / 2 | Seconde fois : +4 Puissance, +4 Degats | 45,1 % |
| Ranger | 2 / 3 | Patience : -1 Degat au duo adverse | 41,3 % |
| Clerc | 2 / 3 | Defaite : +3 PV | 39,7 % |
| Ensorceleur | 2 / 1 | Si un adversaire a des Degats de base >= 3 : -3 Degats au duo adverse | 36,2 % |
| Voleur | 1 / 1 | Si un adversaire a une Puissance de base >= 4 : Puissance +4 | 35,1 % |
| Barde | 1 / 1 | Si Puissance alliee >= 3 : Degats +3 | 29,4 % |

Moyenne 49,0 %, soit un taux d'egalite d'environ 2 % (une egalite compte comme une defaite
des deux cotes, ce qui abaisse mecaniquement la moyenne sous 50 %).

**Ce roster n'est pas equilibre au sens de `versions/duo.md`** : l'ecart va de 29,4 % a
79,0 %, soit pres de 50 points, la ou le critere vise une bande resserree autour de la
moyenne. Ces valeurs sont celles demandees dans `versions/duo.md` et n'ont pas ete retouchees
— la mesure est donnee telle quelle, comme point de depart d'un reglage.

Le moteur du desequilibre est la **Puissance de base**. Comme les 8 utilisations d'une equipe
sont toutes consommees sur les 4 batailles, aucun Combattant ne peut etre mis au banc : sa
Puissance de base pese a chaque partie, alors qu'un Pouvoir conditionnel ne se declenche que
parfois. Les trois Combattants a Puissance 4 occupent les trois premieres places, les trois a
Puissance 1 ou 2 les trois dernieres, et le Guerrier (Puissance 3, aucun Pouvoir) atterrit a
49,5 % : il sert de temoin, et montre qu'a ce niveau de Puissance un Pouvoir nul suffit deja
a faire un Combattant moyen.

Les Pouvoirs conditionnes sur le duo adverse (Voleur, Ensorceleur) sont les plus mal lotis :
ils ne se declenchent qu'a certaines confrontations, et l'IA ne peut pas les anticiper au
moment de choisir son duo. Le Barde souffre du meme probleme cote allie, avec en plus une
Puissance de 1 qui pese a chaque bataille.

Pour reequilibrer, `generate_metagame.py` reste l'outil de mesure :

```
uv run generate_metagame.py -n 40000
```

Rappel de methode : le critere etant relatif, renforcer un Combattant affaiblit tous les
autres — il faut comparer a la moyenne mesuree (ici 49,0 %), pas a 50 %.

## Tests effectues

- **Pouvoirs, un par un** : 35 verifications sur des batailles construites a la main, une par
  Pouvoir du roster et par cas limite — malus de Degats applique une seule fois sur le total
  du duo adverse, plancher a 0 quand Ensorceleur et Mage se cumulent, `puissance_alliee` lue
  sur la base (le Voleur porte a 5 ne reveille pas le Barde), `Contrecoup` du Barbare paye en
  cas de victoire et gratuit en cas de defaite, `Depasser ses limites` declenchant `victoire`
  et `defaite` dans le meme duo (avec temoin sans forcage), `patience` multipliee par le
  numero de la bataille des deux cotes, Pouvoir vide du Guerrier sans incident.
- **Invariants de regles** sur 2 000 parties simulees : utilisations toujours dans `[0, 2]`,
  un duo legal existe toujours, les duos comportent 2 Combattants distincts et disponibles,
  la partie ne depasse jamais 4 batailles, les 7 cartes bataille apparaissent, `Reperage`
  revele exactement 1 Combattant, `Second souffle` rend bien une utilisation au Combattant
  designe, `Depasser ses limites` est effectivement applique au tour suivant (779 occurrences
  observees).
- **API HTTP reelle** (serveur Flask demarre) : 40 parties completes jouees de bout en bout,
  verification de la forme de chaque reponse consommee par le frontend, des phases
  traversees (`choix_duo`, `revelation`, `second_souffle`, `bataille_resolue`), de la
  coherence des sommes de Puissance, de la positivite des Degats infliges, et du rejet propre
  (HTTP 400) de 8 actions invalides — dont les deux nouvelles routes appelees hors phase.
- **Frontend pilote dans un navigateur headless** (Chromium, via le DevTools Protocol) :
  14 parties completes jouees au clic (selection d'equipe → duo → revelation → recharge →
  resultat → ecran de fin) sans aucune erreur JavaScript, avec verification du rendu des
  12 cartes et de leurs Pouvoirs, des 20 ronds de PV, des 8 ronds d'utilisation, des deux
  nouveaux panneaux de choix, et du fait que le bouton « Bataille suivante » reste masque
  tant que le Second souffle n'a pas ete attribue.
- **Equilibrage** mesure sur 40 000 parties (tableau ci-dessus).
