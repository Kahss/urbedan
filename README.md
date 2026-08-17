# Urban Eredan — Prototype (version « champ de bataille »)

Prototype jouable en solo (vs IA) du jeu de societe Urban Eredan (`game.md`), avec un
backend Python (moteur de regles + IA) et un frontend web (HTML/CSS/JS, jouable
uniquement au clic).

Cette branche implemente la version decrite dans `versions/battlefield.md` : les Glyphes
disparaissent, et chaque duel se resout sur une **carte Champ de bataille** commune aux
deux joueurs, revelee seulement une fois les deux Combattants engages.

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
    champs.py               Cartes Champ de bataille : modeles, deck, dos colore
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
**Souterrain** (3). Chaque case porte une valeur de -2 a 6 et, eventuellement, un point
d'Energie (0 ou 1).

Le **dos** de la carte ne montre que la couleur de chaque case — vert si la valeur est
positive, gris si elle est nulle, rouge si elle est negative. C'est la seule information
disponible au moment ou les joueurs engagent leur Combattant : ni les valeurs exactes,
ni la presence d'Energie ne sont connues avant la revelation. Le choix se fait donc sur
une esperance, jamais sur un calcul exact.

Le deck compte **30 cartes : 10 modeles x 3 rotations**. Une rotation reprend les memes
cases decalees d'une Zone ; sur l'ensemble du deck, les 3 Zones voient donc exactement le
meme multi-ensemble de cases. **Aucune Zone n'est structurellement meilleure qu'une
autre**, et deux Combattants dont l'Avantage a la meme taille partent a egalite stricte.

| Modele | Bitume | Hauteur | Souterrain | Dos |
| --- | --- | --- | --- | --- |
| Nuit calme | +3 | +2 ⚡ | 0 ⚡ | vert vert gris |
| Quartier ouvert | +4 | +1 ⚡ | 0 ⚡ | vert vert gris |
| Halo urbain | +2 ⚡ | +1 ⚡ | 0 ⚡ | vert vert gris |
| Terrain conteste | +4 | +2 | -1 ⚡ | vert vert rouge |
| Zone de chantier | +5 | +1 ⚡ | -2 ⚡ | vert vert rouge |
| Couvre-feu | +2 ⚡ | +1 ⚡ | -2 | vert vert rouge |
| Ligne de faille | +6 | +1 | -2 ⚡ | vert vert rouge |
| Nuit blanche | +3 | +2 | +1 ⚡ | vert vert vert |
| Rue barree | +4 | 0 ⚡ | -1 ⚡ | vert gris rouge |
| Terrain condamne | 0 ⚡ | -1 ⚡ | -2 ⚡ | gris rouge rouge |

⚡ = la case porte un point d'Energie. Sur l'ensemble du deck : 1,8 case verte par carte
en moyenne, et **l'Energie est deliberement plus frequente sur les cases grises et rouges
(1,00 et 0,86 par case) que sur les vertes (0,44)**. Subir une mauvaise case reste donc un
lot de consolation qui allume un Pouvoir : le spécialiste condamne au rouge n'y perd pas
tout.

## Deroulement d'un duel

1. La carte du duel est posee face cachee : les deux joueurs voient son **dos**.
2. J1 engage son Combattant, face visible.
3. J2 engage le sien, **en connaissant celui de J1**. L'information cachee, a ce stade,
   ce sont les valeurs du champ de bataille — pas le choix adverse.
4. Le champ de bataille est revele. Chaque Combattant encaisse la valeur et l'Energie des
   seules cases couvertes par son `avantage` : la carte est commune, les cases lues ne le
   sont pas.
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
    "energie_min": 1,
    "effets": [ { "type": "puissance", "cible": "soi", "valeur": 2 } ]
  }
}
```

- `avantage` (obligatoire) : entre 1 et 3 Zones distinctes parmi `1` (Bitume), `2`
  (Hauteur), `3` (Souterrain). C'est la caracteristique structurante de cette version.
- `energie_min` (optionnel, defaut 0) : cout minimum en Energie pour activer le Pouvoir,
  note "X+" — le Pouvoir s'active des lors que l'Energie recoltee sur ses cases est
  superieure ou egale a `energie_min` (`0` ou absent = Pouvoir toujours actif).
  **Contrainte dure : `energie_min` ne doit jamais depasser `len(avantage)`**, sinon le
  Pouvoir est definitivement inactivable (une case porte au plus 1 point d'Energie). Un
  spécialiste a 1 Zone plafonne a 1 Energie.
- `condition` (optionnel) : un des mots-cles Condition de `pouvoirs.csv` —
  `courage`, `riposte`, `vengeance`, `domination`, `victoire`, `defaite`, `surpuissance`.
- `modificateur` (optionnel) : un des mots-cles Modificateur —
  `patience`, `impatience`, `par_energie`, `par_energie_adverse`, `par_energie_en_jeu`,
  `contrecoup`. `par_energie` multiplie la valeur de l'effet par l'Energie recoltee par le
  Combattant lui-meme ; `par_energie_adverse` par celle de l'adversaire ce duel-ci ;
  `par_energie_en_jeu` par la somme des deux.
- `effets` : liste d'effets, chacun avec un `type` :
  - `puissance` / `degats` / `vie` : necessitent `cible` (`soi` ou `adversaire`) et `valeur`
    (entier signe). `vie` modifie les PV du joueur (pas une statistique du Combattant).
  - `stop_pouvoir` / `copie_pouvoir` / `protection` / `echange` : aucun champ supplementaire.
  - `vampirisme` : `valeur` = X (reduit les PV adverses de X, gagne X PV).

Un Pouvoir peut activer plusieurs `effets` (liste), mais un seul `condition` /
`modificateur`.

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
  spécialiste qu'on n'engage que si le dos annonce la bonne couleur.
- **Energie : cases avantagees seulement**. Le Combattant ne recolte que l'Energie des
  cases de son Avantage. L'Energie est donc asymetrique entre les deux Combattants d'un
  meme duel.
- **L'Energie n'apparait pas au dos**. Le dos ne porte que les 3 couleurs, conformement au
  spec. Activer un Pouvoir a seuil reste donc un pari — ce qui a impose d'abaisser
  plusieurs `energie_min` du roster par rapport a la version Glyphes.
- **J2 voit le choix de J1**, conformement a la structure sequentielle de `game.md` : les
  mots-cles Courage et Riposte gardent leur sens. Comme les valeurs du recto restent
  cachees, J2 sait quel Combattant il affronte, pas qui gagnera.
- **Le champ de bataille est commun** aux deux Combattants du duel : une seule carte par
  duel, lue differemment par chacun selon son Avantage.
- **Etancheite de l'information cachee cote serveur** : tant que la phase de choix dure,
  l'API ne serialise que le dos de la carte. Les valeurs et l'Energie n'existent pas cote
  client avant la resolution — il n'y a rien a devoiler en inspectant le trafic reseau.
- **Deck de 30 cartes**, melange, une carte piochee par duel (donc 4 au maximum sur une
  partie), jamais reconstitue. L'interface affiche la **composition du deck** en legende
  (information publique) mais **aucun compteur de cartes restantes** : le but est de
  raisonner en esperance, pas de compter les cartes.
- **Selection d'equipe** : avant chaque partie, le joueur choisit manuellement ses 4
  Combattants parmi les 22 disponibles ; l'IA tire au hasard 4 Combattants distincts
  parmi ceux restants. Le roster complet de chaque joueur est visible par l'autre pendant
  toute la partie.
- **Un seul Pouvoir par Combattant**, actif des lors que l'Energie recoltee atteint son
  seuil `energie_min`. **Ordre de resolution** : J1 resout son Pouvoir avant J2.
- **Stop pouvoir et Copie pouvoir sont generiques** : ils visent toujours l'unique Pouvoir
  de l'adversaire, s'il est actif. Stop pouvoir agit retroactivement si le Pouvoir cible a
  deja ete resolu, par anticipation sinon.
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

## IA

L'IA (`engine/ia.py`) **ne triche pas** : au moment de choisir, elle ne connait que le dos
de la carte, exactement comme le joueur humain. Elle procede par esperance :

1. elle enumere les faces du deck dont le dos correspond a celui revele. La composition du
   deck est publique (affichee en legende), mais elle ne tient volontairement pas compte
   des cartes deja jouees : **elle ne compte pas les cartes**.
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
roster tient dans une fourchette de **45,2 % a 48,9 %** de victoires, centree sur 46,6 %
(le centre est sous 50 % parce qu'environ 7 % des parties se terminent par une egalite).
L'ecart-type de mesure a ce volume est de +/- 0,5 point : le roster est donc converge, a
la granularite pres du point de Puissance.

Trois enseignements sont sortis de l'equilibrage, et ils sont propres a cette version :

**1. Le spécialiste tire un avantage de selection que le generaliste n'a pas.** Sur
27 900 duels simules, le bonus moyen effectivement encaisse est de 1,68 pour un Combattant
a 1 Zone, 2,88 a 2 Zones, 3,61 a 3 Zones — alors que l'esperance a l'aveugle serait de
1,13 / 2,27 / 3,40. Le gain de selection est donc de **+0,55 pour le spécialiste, mais
seulement +0,21 pour le generaliste** : ce dernier encaisse la carte telle qu'elle vient
et ne peut pas choisir son moment. C'est ce qui a impose de remonter la Puissance de base
des profils a 3 Zones en fin d'equilibrage (Cobra, Echo, Surge, Mime derivaient tous vers
44 %).

**2. Gagner des duels et gagner la partie sont deux choses tres differentes.** Les taux de
victoire en duel s'etalent de **14,6 % (Vex) a 76,6 % (Toph)** alors que les taux de
victoire en partie tiennent tous entre 45 et 49 %. Vex perd presque tous ses duels — c'est
precisement son metier, son Pouvoir se declenche sur Defaite.

**3. Un point de Vie gagne vaut moins qu'un point de Vie retire a l'adversaire.** Seuls
les degats peuvent terminer la partie prematurement, et un soin au-dessus du seuil de
victoire est perdu. Mesure sur la version intermediaire : Verve produisait un ecart de PV
net de **+0,49 par duel et ne gagnait que 41,6 % des parties**, quand Vex produisait
**-0,88 et en gagnait 47,6 %**. Corollaire de conception : un Combattant faible qu'on veut
remonter gagne plus a recevoir de la Puissance ou des Degats qu'a voir son soin augmente.

L'avantage du premier joueur est modere : **J1 remporte 53,0 % des duels**.

Note de methode : une boucle de correction automatique (mesurer, corriger d'un point de
Puissance, recommencer) a ete tentee et **n'a pas converge** — elle oscillait, l'etendue
passant de 8,8 a 12,5 points en 8 tours. Un point de Puissance vaut 3 a 5 points de taux
de victoire : le pas est plus large que la bande visee. L'equilibrage final a donc ete
conduit a la main, en utilisant les Degats comme levier fin (environ 2 points) et la
Puissance comme levier grossier.

## Tests effectues

- **Simulation de 30 000 parties** IA contre IA (`generate_metagame.py`), taux de victoire
  par Combattant.
- **Diagnostic sur 27 878 duels** : taux de victoire en duel, Energie et bonus moyens
  recoltes, taux d'alimentation du Pouvoir, contribution du Pouvoir a la Puissance, ecart
  de PV net produit — agrege aussi par taille d'Avantage.
- **Test bout en bout de l'API HTTP** (101 duels sur 30 parties) verifiant :
  - que le recto du champ de bataille (valeurs, Energie, nom du modele) **ne transite
    jamais** avant la resolution, et que le dos revele correspond bien aux couleurs du
    recto ;
  - que `bonus_champ` et `energie` de chaque Combattant valent exactement la somme des
    cases de son `avantage` ;
  - que `detail_puissance` s'ouvre sur la base puis une entree nommee par Zone couverte,
    et que sa somme egale la Puissance finale affichee ;
  - que le vainqueur declare correspond a la comparaison des Puissances finales ;
  - la validite du roster (`avantage` bien forme, `energie_min <= len(avantage)`) et du
    deck (valeurs dans [-2, 6], Energie dans {0, 1}, couleur coherente avec la valeur).
- **Verification de la symetrie du deck** : les 3 Zones presentent une somme de valeurs
  (34) et un total d'Energie (19) rigoureusement identiques sur les 30 cartes.
- **Verification visuelle du frontend** (captures Chromium headless) sur les trois ecrans :
  selection d'equipe, phase de choix (dos colore + pastilles d'Avantage teintees par le
  dos), duel resolu (recto revele, detail du calcul, journal de resolution, legende du
  deck).
