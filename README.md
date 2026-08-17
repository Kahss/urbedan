# Urban Eredan — Prototype (version « champ de bataille »)

Prototype jouable en solo (vs IA) du jeu de societe Urban Eredan (`game.md`), avec un
backend Python (moteur de regles + IA) et un frontend web (HTML/CSS/JS, jouable
uniquement au clic).

Cette branche implemente la version decrite dans `versions/battlefield.md` : les Glyphes
disparaissent, et chaque duel se resout sur une **carte Champ de bataille** commune aux
deux joueurs, dont une seule case est devoilee avant les choix.

**Il n'y a pas d'Energie dans cette version.** Tous les Pouvoirs sont en permanence
actifs ; seule leur `condition` peut les empecher de se declencher.

## Lancer le jeu

Depuis la racine du projet :

```
uv sync
.venv/bin/python backend/app.py
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
    champs.py               Cartes Champ de bataille : modeles, deck, dos
    models.py               Combattants, Joueurs
    powers.py               Moteur generique de resolution des Pouvoirs
    ia.py                   Heuristique de choix de l'IA (quel Combattant engager)
    game.py                 Orchestration d'une Partie (mise en place, duels, IA)
frontend/
  index.html / style.css / app.js   Interface (100% cliquable, sans framework)
generate_metagame.py        Simulation IA contre IA, taux de victoire par Combattant
```

## Le champ de bataille

Une carte comporte **3 cases**, une par Zone : **Bitume** (1), **Hauteur** (2),
**Souterrain** (3). Chaque case porte une valeur de -2 a 6.

Le **dos** de la carte ne devoile **qu'une seule case**, designee par le modele : sa
couleur y apparait, verte si sa valeur est positive, rouge si elle est negative. Les deux
autres restent grises, ce qui signifie « inconnu ». **La case devoilee n'est jamais
nulle**, faute de quoi elle s'afficherait grise elle aussi et serait indistinguable d'une
case inconnue.

Le deck compte **30 cartes : 10 modeles x 3 rotations**. Une rotation reprend les memes
cases decalees d'une Zone, la case devoilee suivant le meme decalage. Sur l'ensemble du
deck, les 3 Zones voient donc exactement le meme multi-ensemble de cases et sont devoilees
exactement aussi souvent (10 fois chacune). **Aucune Zone n'est structurellement meilleure
qu'une autre**, et deux Combattants dont l'Avantage a la meme taille partent a egalite
stricte.

| Modele | Bitume | Hauteur | Souterrain |
| --- | --- | --- | --- |
| Nuit calme | **+3** | +2 | 0 |
| Quartier ouvert | +4 | **+1** | 0 |
| Halo urbain | **+2** | +1 | 0 |
| Terrain conteste | +4 | +2 | **-1** |
| Zone de chantier | **+5** | +1 | -2 |
| Couvre-feu | +2 | +1 | **-2** |
| Ligne de faille | +6 | +1 | **-2** |
| Nuit blanche | +3 | +2 | **+1** |
| Rue barree | **+4** | 0 | -1 |
| Terrain condamne | 0 | **-1** | -2 |

La valeur **en gras** est celle que le modele devoile au dos. 6 modeles devoilent une case
verte, 4 une case rouge : le dos est donc autant une promesse qu'un avertissement. Sur
l'ensemble du deck, 1,8 case verte par carte en moyenne, et une valeur totale de 3,4 par
carte.

## Deroulement d'un duel

1. La carte du duel est posee face cachee : les deux joueurs voient son **dos**, donc la
   couleur de l'unique Zone devoilee.
2. J1 engage son Combattant, face visible.
3. J2 engage le sien, **en connaissant celui de J1**. L'information cachee, a ce stade, ce
   sont les valeurs du champ de bataille — pas le choix adverse.
4. Le champ de bataille est revele. Chaque Combattant encaisse la valeur des seules cases
   couvertes par son `avantage` : la carte est commune, les cases lues ne le sont pas.
5. Resolution des Pouvoirs, comparaison des Puissances, degats du vainqueur.

## Editer / ajouter des Combattants

`data/combattants.json` peut etre modifie a la main puis est recharge automatiquement au
lancement d'une nouvelle partie (pas besoin de redemarrer le serveur). Chaque Combattant
ne possede qu'un seul Pouvoir :

```json
{
  "id": "identifiant_unique",
  "nom": "Nom affiche",
  "puissance": 6,
  "avantage": [1, 2],
  "degats": 3,
  "pouvoir": {
    "description": "Texte affiche sur la carte",
    "condition": null,
    "modificateur": null,
    "effets": [ { "type": "puissance", "cible": "soi", "valeur": 2 } ]
  }
}
```

- `avantage` (obligatoire) : entre 1 et 3 Zones distinctes parmi `1` (Bitume), `2`
  (Hauteur), `3` (Souterrain). C'est la caracteristique structurante de cette version.
- `condition` (optionnel) : un des mots-cles Condition de `pouvoirs.csv` —
  `courage`, `riposte`, `vengeance`, `domination`, `victoire`, `defaite`, `surpuissance`.
  C'est **le seul** moyen d'empecher un Pouvoir de se declencher.
- `modificateur` (optionnel) : `patience`, `impatience` ou `contrecoup`. Les modificateurs
  `par_energie`, `par_energie_adverse` et `par_energie_en_jeu` **n'existent plus** dans
  cette version ; le moteur ne les interprete pas.
- `effets` : liste d'effets, chacun avec un `type` :
  - `puissance` / `degats` / `vie` : necessitent `cible` (`soi` ou `adversaire`) et `valeur`
    (entier signe). `vie` modifie les PV du joueur (pas une statistique du Combattant).
  - `stop_pouvoir` / `copie_pouvoir` / `protection` / `echange` : aucun champ supplementaire.
  - `vampirisme` : `valeur` = X (reduit les PV adverses de X, gagne X PV).

Un Pouvoir peut activer plusieurs `effets` (liste), mais un seul `condition` /
`modificateur`. Le champ `energie_min` n'existe plus.

## Detail du calcul de Puissance / Degats

A la resolution d'un duel, l'API renvoie pour chaque Combattant le detail complet du
calcul (`puissance_txt`, `degats_txt`, affiches sur la carte du duel resolu), sous la
forme `total = X (base) + Y (Bitume) + Z (Hauteur) + W (Pouvoir Nom) ...`. Chaque case du
champ de bataille apparait nommement, puis chaque Pouvoir ayant modifie la valeur, dans
l'ordre ou il a ete applique.

## Hypotheses et choix d'implementation

Certaines regles laissaient place a interpretation ; les choix suivants ont ete tranches
avec l'utilisateur avant developpement :

- **Lecture de l'Avantage : somme**. Le Combattant additionne la valeur de **toutes** les
  cases de son Avantage (et non la meilleure d'entre elles). Avoir 3 Zones donne donc
  beaucoup de valeur mais expose entierement aux cases rouges ; avoir 1 Zone fait un
  spécialiste, qui n'a d'information sur son terrain que quand la Zone devoilee est la
  sienne.
- **Aucune Energie**. Les Pouvoirs sont toujours actifs et leurs valeurs sont fixes. Les
  7 Pouvoirs qui scalaient sur l'Energie ont ete convertis en valeurs fixes calibrees sur
  leur contribution moyenne d'avant (Riff, Iron, Cobra, Echo, Mirage, Surge, Loup).
  Consequence assumee : Mirage (« +2 Puissance par Energie adverse ») et Surge (« par
  Energie en jeu ») perdent leur identite de retournement et de captation, et deviennent
  de simples bonus fixes.
- **Une seule case devoilee au dos**, choisie par le modele de carte, et jamais nulle. Une
  case grise signifie « inconnu », pas « valeur zero » — la distinction est portee par le
  code, ou le dos utilise un jeton `inconnu` distinct du `gris` du recto.
- **La case devoilee tourne avec les valeurs** : les 3 rotations d'un modele devoilent
  chacune une Zone differente. C'est ce qui preserve la symetrie stricte entre les Zones.
- **J2 voit le choix de J1**, conformement a la structure sequentielle de `game.md` : les
  mots-cles Courage et Riposte gardent leur sens. Comme les valeurs du recto restent
  cachees, J2 sait quel Combattant il affronte, pas qui gagnera.
- **Le champ de bataille est commun** aux deux Combattants du duel : une seule carte par
  duel, lue differemment par chacun selon son Avantage.
- **Etancheite de l'information cachee cote serveur** : tant que la phase de choix dure,
  l'API ne serialise que le dos de la carte. Les valeurs n'existent pas cote client avant
  la resolution — il n'y a rien a devoiler en inspectant le trafic reseau.
- **Deck de 30 cartes**, melange, une carte piochee par duel (donc 4 au maximum sur une
  partie), jamais reconstitue. L'interface affiche la **composition du deck** en legende
  (information publique) mais **aucun compteur de cartes restantes** : le but est de
  raisonner en esperance, pas de compter les cartes.
- **Selection d'equipe** : avant chaque partie, le joueur choisit manuellement ses 4
  Combattants parmi les 22 disponibles ; l'IA tire au hasard 4 Combattants distincts
  parmi ceux restants. Le roster complet de chaque joueur est visible par l'autre pendant
  toute la partie.
- **Ordre de resolution** : au sein d'un duel, J1 resout son Pouvoir avant J2.
- **Stop pouvoir et Copie pouvoir sont generiques** : ils visent toujours l'unique Pouvoir
  de l'adversaire. Stop pouvoir agit retroactivement si le Pouvoir cible a deja ete
  resolu, par anticipation sinon.
- **Protection** : annule toutes les modifications deja subies de la part de l'adversaire
  et bloque toute nouvelle modification adverse pour le reste du duel. Ne bloque pas les
  degats de fin de duel.
- **Victoire / Defaite / Surpuissance / Contrecoup** dependent de l'issue du duel : ils
  sont resolus dans une seconde passe, apres determination du vainqueur, et n'influent
  donc jamais sur la comparaison de Puissance du duel en cours.
- **Contrecoup** ne redirige pas l'effet vers soi : il conditionne uniquement le
  declenchement a la victoire, la cible reste celle declaree dans la donnee (comportement
  fixe par le commit `7d7b882`). La donnee de Cascade a ete corrigee en consequence
  (`cible: "soi"`), sans quoi son « Contrecoup : +4 Vie » soignait l'adversaire.
- **Patience / Impatience** se basent sur le numero du duel courant (1 a 4).
- **Copie pouvoir** : limitations POC inchangees (ne copie pas un Pouvoir conditionne par
  l'issue du duel, ni un Pouvoir contenant lui-meme une Copie de pouvoir).
- **Double victoire** (egalite de Puissance) : les deux Combattants remportent le duel et
  infligent chacun leurs Degats ; J2 devient J1 au duel suivant.

## Interface

La carte Combattant est construite autour de son **Pouvoir** : un bloc a fond distinct,
borde a gauche d'un filet colore, dont l'entete reprend la condition (« COURAGE »,
« DOMINATION »...) et le corps l'effet. Ce filet passe a l'or quand la condition est
verifiee dans le contexte du duel en cours.

L'**Avantage** est une bande fine de 3 cellules a droite du nom (B / H / S). Les Zones
couvertes sont opaques et prennent la couleur du dos de la carte du duel ; les Zones hors
Avantage sont effacees. Une fois le duel resolu, la bande passe aux couleurs reelles du
recto. On lit donc d'un coup d'oeil si le Combattant couvre la Zone devoilee, sans que
cette information ecrase la carte.

## IA

L'IA (`engine/ia.py`) **ne triche pas** : au moment de choisir, elle ne connait que le dos
de la carte, exactement comme le joueur humain. Elle procede par esperance :

1. elle enumere les faces du deck dont le dos correspond a celui revele. La composition du
   deck est publique (affichee en legende), mais elle ne tient volontairement pas compte
   des cartes deja jouees : **elle ne compte pas les cartes**. Une seule case etant
   devoilee, ces faces compatibles restent nombreuses : l'incertitude est reelle.
2. pour chaque face possible et chaque Combattant candidat, elle resout **reellement** le
   duel avec le moteur de `powers.py`, sur des Joueurs fictifs, et mesure l'ecart de PV
   qui en resulte. Elle n'a donc pas besoin d'approximer les Pouvoirs : Victoire,
   Surpuissance, Contrecoup, Stop pouvoir, Echange sont evalues exactement — mais sur une
   carte hypothetique.
3. elle retient le Combattant dont l'ecart de PV moyen est le meilleur.

L'information disponible depend du role, et l'IA en tient compte :
- **en J2**, elle connait le Combattant deja engage par J1 : elle evalue directement sa
  reponse ;
- **en J1**, elle ne le connait pas. Les equipes etant face visible, elle suppose que
  l'adversaire repondra au mieux (minimax a un coup) et retient le Combattant dont la
  meilleure reponse adverse coute le moins cher.

Les egalites de score sont tranchees au hasard, pour eviter un jeu totalement previsible.

## Equilibrage

Mesure sur **30 000 parties IA contre IA** (`generate_metagame.py -n 30000`) : tout le
roster tient dans une fourchette de **43,9 % a 48,8 %** de victoires, centree sur 46,2 %
(le centre est sous 50 % parce qu'environ 7 % des parties se terminent par une egalite).
L'ecart-type de mesure a ce volume est de +/- 0,5 point.

Quatre enseignements, dont trois specifiques a ce reglage :

**1. Retirer de l'information au dos penalise specifiquement le spécialiste.** Un
Combattant a 1 Zone ne voit sa Zone devoilee que dans **34 %** des duels, contre 66 % pour
un profil a 2 Zones et 100 % pour un profil a 3 Zones. Il ne peut donc plus choisir son
moment. Mesure : son gain de selection (bonus reellement encaisse moins l'esperance a
l'aveugle) est tombe de **+0,55 a +0,20** par rapport a la version ou les 3 cases etaient
colorees. Le generaliste, lui, est inchange : il encaissait deja la carte telle qu'elle
venait.

**2. L'avantage du premier joueur a disparu.** J1 remportait 53,0 % des duels quand les
3 cases etaient devoilees ; il en remporte **49,6 %** maintenant. Avec moins
d'information, savoir quel Combattant l'adversaire a engage cesse d'etre un avantage
exploitable — l'incertitude sur le terrain domine.

**3. Le levier d'equilibrage d'Echange est inverse.** Le Pouvoir de Furet permute les
totaux : il remporte donc le duel exactement quand il etait en retard. **Baisser sa
Puissance renforce son Pouvoir.** Passe de 5 a 3 de Puissance de base, Furet restait a
53 % de victoires ; c'est en la montant a 8 qu'il est revenu dans la bande. Meme logique
pour ses Degats, qui ne sont que ce qu'il donne a l'adversaire.

**4. Un point de Vie gagne vaut moins qu'un point de Vie retire a l'adversaire.** Seuls
les degats peuvent terminer la partie prematurement, et un soin au-dessus du seuil de
victoire est perdu. Corollaire de conception : un Combattant faible qu'on veut remonter
gagne plus a recevoir de la Puissance ou des Degats qu'a voir son soin augmente.

A noter aussi : les taux de victoire **en duel** s'etalent de 21 % (Cobra) a 75 % (Toph)
alors que les taux de victoire **en partie** tiennent tous entre 44 et 49 %. Gagner des
duels et gagner la partie restent deux choses differentes — Cobra perd presque tous ses
duels et draine des PV a chaque fois.

Note de methode : une boucle de correction automatique (mesurer, corriger d'un point de
Puissance, recommencer) avait ete tentee lors du reglage precedent et **n'a pas
converge** — elle oscillait, l'etendue passant de 8,8 a 12,5 points en 8 tours. Un point
de Puissance vaut 3 a 5 points de taux de victoire : le pas est plus large que la bande
visee. L'equilibrage est donc conduit a la main, en utilisant les Degats comme levier fin
(environ 2 points) et la Puissance comme levier grossier.

## Tests effectues

- **Simulation de 30 000 parties** IA contre IA (`generate_metagame.py`), taux de victoire
  par Combattant.
- **Diagnostic sur 26 705 duels** : taux de victoire en duel, frequence a laquelle la Zone
  devoilee est couverte, bonus moyen encaisse, contribution du Pouvoir a la Puissance,
  ecart de PV net produit — agrege aussi par taille d'Avantage.
- **Test bout en bout de l'API HTTP** (88 duels sur 30 parties) verifiant :
  - que le recto du champ de bataille (valeurs, nom du modele) **ne transite jamais** avant
    la resolution ;
  - qu'exactement **une** case est coloree au dos, qu'elle est verte ou rouge (jamais
    grise), et que le dos revele correspond bien a la case annoncee du recto ;
  - que `bonus_champ` vaut exactement la somme des cases de l'`avantage` du Combattant ;
  - que `detail_puissance` s'ouvre sur la base puis une entree nommee par Zone couverte,
    et que sa somme egale la Puissance finale affichee ;
  - que le vainqueur declare correspond a la comparaison des Puissances finales ;
  - **l'absence totale d'Energie** : aucun `energie_min` dans le roster, aucun
    modificateur `par_energie*`, aucune Energie sur les cases du deck ni dans les infos de
    duel, et aucune mention d'« Energie insuffisante » dans les journaux de resolution.
- **Verification de la symetrie du deck** : les 3 Zones presentent une somme de valeurs
  (34) identique et sont devoilees exactement 10 fois chacune sur les 30 cartes.
- **Verification du rendu par le DOM** (et non a l'oeil) : les classes CSS produites par la
  bande d'Avantage sont bien `dos-inconnu` pour les Zones non devoilees pendant la phase de
  choix, et suivent les couleurs reelles du recto apres resolution ; le decoupage
  condition / effet de la description du Pouvoir est correct sur les trois formes
  rencontrees.
- **Verification visuelle du frontend** (captures Chromium headless) sur les trois ecrans :
  selection d'equipe, phase de choix (une seule case coloree au dos), duel resolu (recto
  revele, detail du calcul, journal, legende du deck).
