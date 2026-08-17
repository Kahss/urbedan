# Urban Eredan — Prototype

Prototype jouable en solo (vs IA) du jeu de societe Urban Eredan (`game.md`), avec un
backend Python (moteur de regles + IA) et un frontend web (HTML/CSS/JS, jouable
uniquement au clic).

Cette branche implemente la version **"draft de des"** decrite dans
`versions/dice_draft.md` : les cartes Glyphes ont disparu, les Combattants n'ont plus de
Puissance imprimee mais une **initiative**, et chaque duel commence par le lancer d'un
pool central de 6 des que les deux joueurs se partagent en draftant a tour de role.

## Lancer le jeu

L'environnement virtuel est gere par `uv` (`.venv/` a la racine) :

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
    des.py                  Definition des 3 des, composition du pool, jet
    models.py               Combattants, Joueurs
    powers.py               Moteur generique de resolution des Pouvoirs
    ia.py                   Heuristique de l'IA (choix du Combattant, puis du de)
    game.py                 Orchestration d'une Partie (tirage, choix, draft, duels)
frontend/
  index.html / style.css / app.js   Interface (100% cliquable, sans framework)
generate_metagame.py        Simulation IA vs IA et statistiques de victoire par Combattant
```

## Les des et le pool central

Chaque de est un de a 6 faces portant, sur chaque face, un couple **Puissance / Energie**
note `X/Y` :

| De | Faces | Moyenne |
| --- | --- | --- |
| Rouge | 5/0 5/0 4/0 4/0 2/0 2/0 | 3,67 P / 0,00 E |
| Bleu | 3/1 3/1 1/2 1/2 0/2 0/2 | 1,33 P / 1,67 E |
| Violet | 4/1 4/0 3/1 3/0 2/0 1/1 | 2,83 P / 0,50 E |

Au debut de chaque duel, un pool central de **6 des** est lance : toujours deux rouges,
deux bleus et deux violets (`des.COMPOSITION_POOL`). Le resultat est immediatement visible
des deux joueurs — c'est une information publique, et elle est connue **avant** le choix
des Combattants. Le catalogue des des est expose par `GET /api/des` et affiche en legende
dans l'interface.

## Deroulement d'un duel

1. **Tirage** : le pool de 6 des est lance (automatique, aucune decision).
2. **Choix des Combattants** : J1 engage le sien en voyant le pool ; J2 engage le sien en
   voyant le pool *et* le Combattant de J1.
3. **Draft** : le Combattant de meilleure **initiative** prend un de le premier (J1 en cas
   d'egalite), puis les joueurs alternent strictement jusqu'a 3 des chacun. Le premier
   drafteur prend donc les rangs 1, 3 et 5 ; le second les rangs 2, 4 et 6. Le pool est
   integralement reparti.
4. **Resolution** : la Puissance et l'Energie de chaque Combattant sont la somme de
   celles de ses 3 des, puis les Pouvoirs s'appliquent.

## Editer / ajouter des Combattants

`data/combattants.json` peut etre modifie a la main puis rechargé automatiquement au
lancement d'une nouvelle partie (pas besoin de redemarrer le serveur). Chaque Combattant
possede un seul Pouvoir :

```json
{
  "id": "identifiant_unique",
  "nom": "Nom affiche",
  "initiative": 5,
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

- `initiative` : entier. Le Combattant avec la plus haute initiative drafte en premier ;
  a egalite, c'est celui de J1. C'est de loin la caracteristique la plus puissante du
  jeu (voir "Equilibrage" plus bas).
- `degats` : valeur fixe imprimee sur la carte, infligee aux PV adverses par le vainqueur
  du duel (eventuellement modifiee par les Pouvoirs).
- `energie_min` (optionnel, defaut 0) : cout minimum en Energie pour activer le Pouvoir,
  note "X+" — le Pouvoir s'active des lors que l'Energie **totale des 3 des draftes** est
  superieure ou egale a `energie_min` (`0` ou absent = Pouvoir toujours actif).
- `condition` (optionnel) : un des mots-cles Condition de `pouvoirs.csv` —
  `courage`, `riposte`, `vengeance`, `domination`, `victoire`, `defaite`, `surpuissance`.
- `modificateur` (optionnel) : un des mots-cles Modificateur —
  `patience`, `impatience`, `par_energie`, `par_energie_adverse`, `par_energie_en_jeu`,
  `contrecoup`. `par_energie` multiplie la valeur de l'effet par l'Energie obtenue par le
  Combattant lui-meme ; `par_energie_adverse` par celle de l'adversaire ce duel-ci ;
  `par_energie_en_jeu` par la somme des deux.
- `effets` : liste d'effets, chacun avec un `type` :
  - `puissance` / `degats` / `vie` : necessitent `cible` (`soi` ou `adversaire`) et `valeur`
    (entier signe). `vie` modifie les PV du joueur (pas une statistique du Combattant).
  - `stop_pouvoir` / `copie_pouvoir` / `protection` : aucun champ supplementaire.
  - `echange` : aucun champ supplementaire (echange Puissance/Degats entre les 2
    Combattants du duel).
  - `vampirisme` : `valeur` = X (reduit les PV adverses de X, gagne X PV).

Un Pouvoir peut activer plusieurs `effets` (liste), mais un seul `condition` /
`modificateur`.

## Detail du calcul de Puissance / Degats

A la resolution d'un duel, l'API renvoie pour chaque Combattant le detail complet du
calcul (`puissance_txt`, `degats_txt`, affiches sur la carte du duel resolu), sous la
forme `total = X (Rouge) + Y (Bleu) + Z (Pouvoir Nom) ...`. **Chaque de drafte** apparait
comme une ligne separee (y compris ceux qui sortent 0 Puissance), suivi de chaque Pouvoir
ayant modifie la valeur, dans l'ordre ou il a ete applique.

La Puissance totale n'est pas bornee a 0 : un Pouvoir de reduction important peut faire
passer un Combattant en Puissance negative. Seuls les Degats sont bornes a 0 au moment de
l'application.

## Hypotheses et choix d'implementation

Certaines regles de `versions/dice_draft.md` laissaient place a interpretation ; les
choix suivants ont ete valides avec l'utilisateur avant developpement :

- **Le pool est relance a chaque duel** (le spec parle du "pool central tire au debut du
  round"), et le tirage est automatique : ce n'est pas une decision de joueur.
- **L'initiative ne sert qu'a l'ordre du draft.** Elle ne departage pas les egalites de
  Puissance (une egalite reste une double victoire, comme dans `game.md`) et ne change
  pas l'ordre de resolution des Pouvoirs (J1 resout avant J2).
- **Alternance stricte** A-B-A-B-A-B, lecture litterale de "a tour de role" : le premier
  drafteur prend les rangs 1, 3 et 5.
- **Valeurs d'initiative** : derivees de l'inverse de l'ancienne Puissance de base (les
  gros frappeurs draftent en dernier), les egalites de tier etant tranchees par le lore.
  Quatre exceptions assumees, imposees par la nature du Pouvoir plutot que par l'ancienne
  Puissance (voir "Equilibrage") : Gambit, Cascade et Verve, dont le Pouvoir ne se
  declenche qu'en cas de victoire, sont rapides ; Furet, dont l'Echange veut au contraire
  une main faible, est lent.
- **Les Degats restent une valeur fixe imprimee** sur la carte : seule la Puissance est
  passee aux des.
- **Information au moment du choix** : J1 engage son Combattant, puis J2 engage le sien
  en voyant celui de J1 ; les deux voient le pool depuis le debut. Seule reste inconnue,
  pour J1, l'identite du Combattant adverse.
- **Un seul Pouvoir par Combattant**, actif des lors que l'Energie totale des des draftes
  atteint `energie_min`. **Ordre de resolution** : J1 resout son Pouvoir avant J2.
- **Stop pouvoir et Copie pouvoir sont generiques** : ils visent toujours l'unique Pouvoir
  de l'adversaire, s'il est actif. Stop pouvoir agit retroactivement si ce Pouvoir a deja
  ete resolu, ou par anticipation sinon.
- **Protection** : annule toutes les modifications deja subies de la part de l'adversaire
  (retroactif) et bloque toute nouvelle modification adverse pour le reste du duel. Ne
  bloque pas les degats de fin de duel.
- **Victoire / Defaite / Surpuissance / Contrecoup** : resolus dans une seconde passe,
  apres determination du/des vainqueur(s) ; ils n'influent donc jamais sur la comparaison
  de Puissance du duel en cours.
- **Contrecoup** : l'effet, ecrit comme visant l'adversaire, est redirige vers le
  Combattant lui-meme s'il remporte le duel, et ne se produit pas sinon (conforme a
  `pouvoirs.csv`).
- **Patience** : multiplie par le numero du duel courant (1 a 4). **Impatience** :
  multiplie par le nombre de duels restants, celui-ci compris.
- **Copie pouvoir** : copie le Pouvoir actif de l'adversaire et l'execute du point de vue
  du copieur. Limitations POC : copier un Pouvoir conditionne par l'issue du duel ou par
  Contrecoup n'est pas supporte, ni copier un Pouvoir qui contient lui-meme une Copie.
- **Equipe visible** : le roster complet de chaque joueur est visible par l'autre pendant
  toute la partie, initiatives et Pouvoirs compris.

## IA

L'IA (`engine/ia.py`) prend deux decisions par duel. Le pool etant lance avant le choix
des Combattants, les deux se raisonnent sur une information quasi complete.

- **Choix du de** (`choisir_de`) : pour chaque de disponible, l'IA calcule le gain
  marginal qu'il apporte a sa propre marge de Puissance, augmente de la moitie du gain
  qu'il aurait apporte a l'adversaire (privation). L'Energie n'etant plus aleatoire ici,
  l'activation du Pouvoir et son scaling `par_energie` sont calcules exactement.
- **Choix du Combattant** (`choisir_combattant`) : pour chaque Combattant disponible,
  l'IA **simule le draft complet** qui suivrait (meme heuristique des deux cotes, ordre
  donne par les initiatives) sur le pool reellement tire, puis note le duel obtenu. C'est
  ce qui lui permet de valoriser correctement l'initiative. Quand elle joue en second,
  elle connait le Combattant adverse ; sinon elle moyenne sur ceux encore disponibles en
  face.
- Courage / Riposte / Vengeance / Domination sont evalues immediatement ; Victoire /
  Defaite / Surpuissance / Contrecoup dependent de l'issue du duel et ne sont jamais
  comptes. Echange est estime exactement. Stop pouvoir, Protection et Copie pouvoir sont
  croises entre les deux estimations d'un meme duel.

Les egalites de score sont tranchees au hasard lors des vraies decisions, et de facon
deterministe dans les simulations de draft (pour qu'evaluer un Combattant ne dependent
pas du hasard).

## Equilibrage

```
.venv/bin/python generate_metagame.py -n 20000
```

**L'initiative est la caracteristique dominante de cette version**, consequence directe
de l'alternance stricte : celui qui choisit en 1er, 3e et 5e prend le dessus du pool.
Avec un roster naif (initiatives derivees mecaniquement de l'ancienne Puissance, Degats
inchanges), le premier drafteur remportait **83 % des duels** et l'etendue des taux de
victoire atteignait 36 points (Gambit 22 %, Nova 58 %).

Le contrepoids existe pourtant dans le design lui-meme : **le premier drafteur prend la
Puissance, le second herite de l'Energie.** Mesure sur le roster final, le premier
drafteur finit a 10,7 de Puissance contre 9,2, mais a seulement 1,8 d'Energie contre 2,5.
Un Combattant lent dont le Pouvoir scale sur l'Energie recupere donc largement son retard.

Trois regles de conception en decoulent :

- **Un Pouvoir conditionne par la victoire (Victoire, Surpuissance, Contrecoup) exige une
  initiative haute.** Avec une initiative basse, le Combattant perd la plupart de ses
  duels et son Pouvoir ne se declenche jamais : Gambit (initiative 1, Surpuissance)
  tombait a 22 % de victoire malgre 6 Degats. Le passer a l'initiative 9 l'a ramene dans
  la moyenne. C'est l'origine des quatre exceptions a la regle de derivation des
  initiatives.
- **Un Pouvoir qui n'a pas besoin de gagner (Protection, Stop pouvoir, Vampirisme,
  Echange, tout ce qui scale `par_energie`) supporte tres bien une initiative basse** —
  c'est meme la seule facon de rendre un Combattant lent viable. Furet (initiative 2)
  gagne 74 % de ses duels quand il drafte en second : il laisse la Puissance a
  l'adversaire, puis l'echange.
- **Les Degats sont le contrepoids chiffre de l'initiative** : plus un Combattant drafte
  tot, moins il doit frapper fort. Le roster suit cette courbe (Nitro, initiative 10,
  1 Degat ; Mime et Verrou, initiative 3-4, 6-7 Degats).

Apres equilibrage, le roster fourni tient dans une fourchette de **42,7 % a 52,2 %**
(centre autour de 47,2 %, environ 5 % des parties etant nulles et ne comptant pour
personne), et l'avantage du premier drafteur est retombe de 83 % a **72,6 %**. C'est plus
etale que la version "des par personnage" (±3,5 points contre ±4,5 ici) : cette version
reste structurellement plus swingy, une bonne part de l'issue d'un duel se jouant a
l'ordre du draft.

**Variante testee** : un draft serpent (A-B-B-A-A-B) ramene l'avantage du premier
drafteur a **59,1 %** (Puissance 9,9 contre 9,8, quasi equilibre). Attention toutefois :
mesuree sur le roster actuel, qui a ete equilibre *pour* l'alternance stricte, cette
variante ouvre l'etendue des taux de victoire de 13,8 a 18,2 points — les Combattants
lents y sont surpayes en Degats. Passer au serpent demanderait donc de reprendre la
courbe Degats/initiative. La bascule elle-meme tient en quelques lignes dans
`Partie._attribuer_de` (`engine/game.py`).

## Tests effectues

- Simulation de 20 000 parties completes via le moteur Python (sans crash), avec releve
  des taux de victoire par Combattant.
- Diagnostic dedie du draft sur 9 200 duels : taux de victoire du premier drafteur, ecart
  de Puissance et d'Energie entre premier et second, profil par Combattant (frequence de
  premier choix, victoires en duel selon la position de draft).
- Comparaison chiffree alternance stricte / draft serpent a graine aleatoire identique,
  refaite sur le roster final.
- Simulation d'une partie complete via l'API HTTP reelle (serveur Flask demarre),
  verifiant : composition du pool (2 des de chaque couleur), rejet propre (HTTP 400) d'une
  action invalide, **alternance stricte** (le premier drafteur obtient bien les rangs 1, 3
  et 5), coherence de l'ordre de draft avec les initiatives, repartition integrale du pool,
  et coherence des totaux Puissance/Energie avec les des draftes.
- Verification visuelle du frontend dans un navigateur (Chromium headless) sur les trois
  ecrans : selection d'equipe, draft en cours, duel resolu.
