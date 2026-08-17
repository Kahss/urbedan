# Urban Eredan — Prototype

Prototype jouable en solo (vs IA) du jeu de societe Urban Eredan (`game.md`), avec un
backend Python (moteur de regles + IA) et un frontend web (HTML/CSS/JS, jouable
uniquement au clic).

Cette branche implemente la version **"des par personnage"** decrite dans
`versions/dice_by_characters.md` : les cartes Glyphes ont disparu, les Combattants n'ont
plus de Puissance imprimee, et leur Puissance / Energie proviennent du jet d'un pool de
des propre a chaque duel.

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
    des.py                  Definition des 6 des, jet, statistiques
    models.py               Combattants, Joueurs
    powers.py               Moteur generique de resolution des Pouvoirs
    ia.py                   Heuristique de choix de l'IA (Combattant)
    game.py                 Orchestration d'une Partie (mise en place, duels, IA)
frontend/
  index.html / style.css / app.js   Interface (100% cliquable, sans framework)
generate_metagame.py        Simulation IA vs IA et statistiques de victoire par Combattant
```

## Les des

Chaque de est un de a 6 faces portant, sur chaque face, un couple **Puissance / Energie**
note `X/Y`. Trois couleurs, deux teintes chacune :

| De | Faces | Moyenne |
| --- | --- | --- |
| Rouge clair | 3/0 3/0 2/0 2/0 1/0 1/0 | 2,00 P / 0,00 E |
| Rouge fonce | 5/0 5/0 4/0 4/0 2/0 2/0 | 3,67 P / 0,00 E |
| Bleu clair | 1/1 1/1 0/1 0/1 0/1 0/1 | 0,33 P / 1,00 E |
| Bleu fonce | 3/1 3/1 1/2 1/2 0/2 0/2 | 1,33 P / 1,67 E |
| Violet clair | 2/0 2/0 1/1 1/1 1/0 0/1 | 1,17 P / 0,50 E |
| Violet fonce | 4/1 4/0 3/1 3/0 2/0 1/1 | 2,83 P / 0,50 E |

La couleur annonce le type de ressource (rouge = Puissance, bleu = Energie, violet =
melange), la teinte la quantite (clair = faible, fonce = elevee). Les faces sont
volontairement repetitives pour limiter la variance des jets. Le catalogue est expose par
`GET /api/des` et affiche en legende dans l'interface.

## Composition du pool d'un duel

Une fois les deux Combattants engages :

```
pool du Combattant A = des personnels de A + des adverses de B
pool du Combattant B = des personnels de B + des adverses de A
```

Chaque joueur lance son pool ; la somme des Puissances obtenues est sa Puissance de
depart pour le duel, la somme des Energies est l'Energie dont il dispose pour activer son
Pouvoir. Les dons croises font tout l'arbitrage du choix de Combattant : un Combattant
peut etre tres fort avec deux des personnels fonces mais offrir un de fonce a
l'adversaire ; un autre peut se reveler a double tranchant en donnant a l'adversaire
l'Energie qui activera le Pouvoir de celui-ci.

## Editer / ajouter des Combattants

`data/combattants.json` peut etre modifie a la main puis rechargé automatiquement au
lancement d'une nouvelle partie (pas besoin de redemarrer le serveur). Chaque Combattant
possede un seul Pouvoir :

```json
{
  "id": "identifiant_unique",
  "nom": "Nom affiche",
  "degats": 3,
  "des_personnels": ["violet_fonce", "bleu_clair"],
  "des_adverses": ["rouge_clair"],
  "pouvoir": {
    "description": "Texte affiche sur la carte",
    "condition": null,
    "modificateur": null,
    "energie_min": 1,
    "effets": [ { "type": "puissance", "cible": "soi", "valeur": 2 } ]
  }
}
```

- `des_personnels` / `des_adverses` : listes de types de des parmi `rouge_clair`,
  `rouge_fonce`, `bleu_clair`, `bleu_fonce`, `violet_clair`, `violet_fonce`. Un type
  inconnu fait echouer le chargement au demarrage du serveur. Les deux listes peuvent
  etre vides. En moyenne sur le roster, un Combattant a deux des personnels et un de
  adverse.
- `degats` : valeur fixe imprimee sur la carte, infligee aux PV adverses par le vainqueur
  du duel (eventuellement modifiee par les Pouvoirs).
- `energie_min` (optionnel, defaut 0) : cout minimum en Energie pour activer le Pouvoir,
  note "X+" — le Pouvoir s'active des lors que l'Energie **totale obtenue au jet** est
  superieure ou egale a `energie_min` (`0` ou absent = Pouvoir toujours actif, meme avec
  une Energie de 0).
- `condition` (optionnel) : un des mots-cles Condition de `pouvoirs.csv` —
  `courage`, `riposte`, `vengeance`, `domination`, `victoire`, `defaite`, `surpuissance`.
- `modificateur` (optionnel) : un des mots-cles Modificateur —
  `patience`, `impatience`, `par_energie`, `par_energie_adverse`, `par_energie_en_jeu`,
  `contrecoup`. `par_energie` multiplie la valeur de l'effet par l'Energie obtenue par le
  Combattant lui-meme (ex : "+1 Puissance / Energie") ; `par_energie_adverse` multiplie
  par l'Energie obtenue par l'adversaire ce duel-ci ; `par_energie_en_jeu` multiplie par
  la somme des deux Energies (soi + adversaire). Dans tous les cas, combine a
  `energie_min`, cela permet un Pouvoir qui necessite un minimum d'Energie propre pour
  s'activer tout en scalant sur une Energie differente (la sienne, celle de l'adversaire,
  ou le total des deux).
- `effets` : liste d'effets, chacun avec un `type` :
  - `puissance` / `degats` / `vie` : necessitent `cible` (`soi` ou `adversaire`) et `valeur`
    (entier signe). `vie` modifie les PV du joueur (pas une statistique du Combattant).
  - `stop_pouvoir` : aucun champ supplementaire (generique, voir plus bas).
  - `copie_pouvoir` : aucun champ supplementaire (generique, voir plus bas).
  - `protection` : aucun champ supplementaire.
  - `echange` : aucun champ supplementaire (echange Puissance/Degats entre les 2
    Combattants du duel).
  - `vampirisme` : `valeur` = X (reduit les PV adverses de X, gagne X PV).

Un Pouvoir peut activer plusieurs `effets` (liste), mais un seul `condition` /
`modificateur`.

**L'Energie totale obtenue au jet determine si l'unique Pouvoir du Combattant s'active**,
en la comparant a son seuil `energie_min`. Un Combattant n'a donc jamais plus d'un
Pouvoir actif par duel (hors effet de Copie pouvoir). Concevoir un personnage revient a
choisir ses des personnels, les des qu'il concede a l'adversaire, ses Degats, un unique
Pouvoir et son cout en Energie — sachant que l'Energie qu'il pourra reunir depend aussi
des des que l'adversaire lui donnera.

## Detail du calcul de Puissance / Degats

A la resolution d'un duel, l'API renvoie pour chaque Combattant le detail complet du
calcul (`puissance_txt`, `degats_txt`, affiches sur la carte du duel resolu), sous la
forme `total = X (de Rouge fonce) + Y (de Bleu clair) + Z (Pouvoir Nom) ...`. **Chaque de
du jet** apparait comme une ligne separee (y compris ceux qui sortent 0 Puissance, pour
que le detail se relise de en de face au jet affiche), suivi de chaque Pouvoir ayant
modifie la valeur, dans l'ordre ou il a ete applique. Cela permet de verifier precisement
d'ou vient un nombre qui semblerait incoherent au premier abord.

La Puissance totale n'est pas bornee a 0 : un Pouvoir de reduction important (ex : Iron)
peut faire passer un Combattant en Puissance negative. Seuls les Degats sont bornes a 0
au moment de l'application.

## Hypotheses et choix d'implementation

Certaines regles de `game.md` / `pouvoirs.csv` laissaient place a interpretation ; les
choix suivants ont ete valides ou tranches avec l'utilisateur avant developpement :

- **Selection d'equipe** : avant chaque partie, le joueur choisit manuellement ses 4
  Combattants parmi tous ceux disponibles (22 fournis) ; l'IA tire au hasard 4
  Combattants distincts parmi ceux restants.
- **Les Degats restent une valeur fixe imprimee** sur la carte : seule la Puissance est
  passee aux des.
- **Information au moment du choix** : l'ordre de choix est celui de la version
  precedente — J1 engage son Combattant, puis J2 engage le sien **en voyant celui de
  J1**. Comme il n'y a plus de Glyphe cache, J2 connait donc les deux pools de des exacts
  avant de choisir ; seul le jet reste aleatoire. C'est la contrepartie assumee de la
  disparition de l'information cachee.
- **Un seul Pouvoir par Combattant** : chaque Combattant ne possede qu'un unique
  Pouvoir, actif des lors que l'Energie totale du jet atteint son seuil `energie_min`
  (note "X+"). **Ordre de resolution** : au sein d'un duel, J1 resout son Pouvoir (s'il
  est actif) avant que J2 ne resolve le sien.
- **Stop pouvoir et Copie pouvoir sont generiques** : ils visent toujours l'unique
  Pouvoir de l'adversaire, s'il est actif (Energie obtenue >= son seuil `energie_min`).
  Si l'adversaire n'a pas atteint ce seuil (Pouvoir inactif), il n'y a rien a annuler ni
  a copier.
- **Stop pouvoir** : agit retroactivement si le Pouvoir cible a deja ete resolu (le cas
  lorsque J2 vise le Pouvoir de J1, deja joue), ou par anticipation sinon (J1 vise le
  Pouvoir de J2 qui n'a pas encore joue). Cela fonctionne aussi pour annuler
  retroactivement un Echange deja resolu (le calcul du Pouvoir Echange est trace comme
  n'importe quel autre effet, via des deltas Puissance/Degats plutot qu'une permutation
  directe non tracable).
- **Protection** : annule toutes les modifications deja subies de la part de
  l'adversaire (retroactif) et bloque toute nouvelle modification adverse (puissance,
  degats, vie, stop pouvoir, copie pouvoir) pour le reste de la resolution du duel. Ne
  bloque pas les degats de fin de duel (rupture des PV du vaincu), qui ne sont pas une
  "modification de Pouvoir" mais l'application de la regle de base.
- **Victoire / Defaite / Surpuissance / Contrecoup** : ces Pouvoirs dependent de l'issue
  du duel (qui n'est connue qu'apres comparaison des Puissances totales). Ils sont donc
  resolus dans une seconde passe, apres determination du/des vainqueur(s), et n'influent
  donc jamais sur la comparaison de Puissance du duel en cours (uniquement sur les
  Degats/PV/Vie).
- **Patience** : multiplie la valeur de l'effet par le numero du duel courant dans la
  partie (1 a 4). **Impatience** : multiplie par le nombre de duels restants a jouer,
  celui-ci compris (`duels_max - duel_numero + 1`, soit 4 au duel 1, 1 au duel 4).
- **Par energie** : multiplie la valeur de l'effet par l'Energie totale obtenue au jet
  par le Combattant qui possede ce Pouvoir (ex : Echo, Cobra, Iron, Riff). Combine a
  `energie_min`, cela permet un Pouvoir qui necessite un minimum d'Energie pour
  s'activer, et dont l'effet croit ensuite avec l'Energie obtenue au-dela de ce seuil.
- **Par energie adverse** : multiplie la valeur de l'effet par l'Energie obtenue par
  l'adversaire ce duel-ci (ex : Mirage, qui retourne contre l'adversaire l'Energie que
  celui-ci a tiree — Energie a laquelle Mirage contribue volontairement en lui donnant un
  de bleu fonce).
- **Par energie en jeu** : multiplie la valeur de l'effet par la somme des deux Energies
  obtenues ce duel-ci (la sienne et celle de l'adversaire) (ex : Surge).
- **Contrecoup** : l'effet, normalement dirige vers l'adversaire, s'applique a
  soi-meme uniquement si le Combattant remporte le duel (sinon il ne se produit pas).
- **Copie pouvoir** : copie la definition du Pouvoir actuellement actif de l'adversaire
  (effets, condition, modificateur) et l'execute du point de vue du copieur (`soi` =
  copieur, `adversaire` = adversaire du copieur). Limitations POC : copier un Pouvoir
  conditionne par l'issue du duel (Victoire/Defaite/Surpuissance) ou par Contrecoup n'est
  pas supporte (ex : Nova copiant le Pouvoir de Vex, conditionne par Defaite) ; copier un
  Pouvoir qui contient lui-meme une Copie de pouvoir n'est pas supporte non plus (ex :
  Nova face a Mime), pour eviter une recursion infinie puisque l'adversaire cible ne
  change jamais d'une copie a l'autre ; copier un Pouvoir deja annule par un Stop pouvoir
  echoue egalement (rien a copier).
- **Mot-cle "Attaque"** (`pouvoirs.csv`) : `game.md` ne definit que les statistiques
  Puissance et Degats pour un Combattant (pas d'"Attaque" separee). Le mot-cle
  "+/- Attaque" est donc traite comme un synonyme de "+/- Puissance".
- **Double victoire** (egalite de Puissance) : les deux Combattants remportent le duel et
  infligent chacun leurs Degats ; le joueur J2 du duel devient J1 du duel suivant (et
  inversement), conformement a `game.md`.
- **Equipe visible** : le roster complet (les 4 Combattants, utilises ou non) de chaque
  joueur est visible par l'autre pendant toute la partie, des et Pouvoirs compris.

## IA

L'IA (`engine/ia.py`) choisit, parmi ses Combattants disponibles, celui qui maximise une
**marge** estimee (sa Puissance moins celle de l'adversaire), et non plus sa seule
Puissance : puisque les des adverses inscrits sur la carte engagee sont offerts a
l'adversaire, un bon Combattant peut etre un mauvais choix ce tour-ci.

- **Puissance** : esperance exacte de chaque pool (somme des moyennes des des).
- **Energie** : la distribution du total d'Energie d'un pool est calculee exactement par
  convolution des distributions de chaque de. On en tire la probabilite d'atteindre le
  seuil `energie_min`, et l'Energie moyenne *sachant* ce seuil atteint (utilisee par
  `par_energie`). Chaque effet est pondere par cette probabilite d'activation.
- Courage / Riposte / Vengeance / Domination sont evalues immediatement (role du duel,
  PV courants) ; Victoire / Defaite / Surpuissance / Contrecoup dependent de l'issue du
  duel (inconnue au moment du choix) et ne sont donc jamais comptes.
- **Echange** est estime exactement en esperance (les deux pools sont connus) : il vaut
  l'ecart de Puissance entre les deux camps, et l'ecart de Degats.
- **Stop pouvoir / Protection / Copie pouvoir** sont croises entre les deux estimations
  d'un meme duel : un Stop probable rabote le gain adverse, une Protection annule la part
  du gain adverse qui vise ce cote-ci, une Copie ajoute au copieur le gain immediat
  d'en face.
- Quand l'IA joue en second, elle connait le Combattant adverse, donc les deux pools
  exacts. Quand elle joue en premier, elle moyenne son evaluation sur les Combattants
  encore disponibles en face ; elle ne cherche pas a anticiper que l'adversaire
  choisira ensuite le meilleur contre.

Les egalites de score sont tranchees au hasard, pour eviter un jeu totalement
previsible.

## Equilibrage du roster

`generate_metagame.py` simule des parties completes jouees par l'heuristique IA des deux
cotes et donne le pourcentage de victoire de chaque Combattant (un Combattant "gagne" des
lors que son equipe gagne) :

```
.venv/bin/python generate_metagame.py -n 20000
```

Sur 20 000 parties, le roster fourni tient dans une fourchette de **43,3 % a 49,3 %**.
Attention a la lecture : environ 7 % des parties sont nulles (egalite de PV apres 4
duels) et ne comptent comme victoire pour personne, ce qui centre la distribution autour
de **46,4 %** et non de 50 %. La fourchette cible "45-55 %" heritee de la version
precedente doit donc etre lue comme "centre +/- 5 points", soit environ 41,5-51,5 %.

## Tests effectues

- Simulation de 20 000 parties completes via le moteur Python (sans crash), avec releve
  des taux de victoire par Combattant.
- Diagnostic complementaire par Combattant (frequence d'engagement, taux de victoire en
  duel, Energie moyenne obtenue, taux d'activation du Pouvoir, Puissance moyenne).
- Simulation d'une partie complete via l'API HTTP reelle (serveur Flask demarre),
  verifiant le cycle choix Combattant (resolution automatique une fois les deux choisis)
  -> duel suivant -> fin de partie, le rejet propre (HTTP 400) d'une action invalide, la
  coherence des totaux Puissance/Energie avec les des du jet, et la **composition croisee
  des pools** (des personnels du Combattant + des adverses de celui d'en face, dans cet
  ordre, avec la bonne origine).
- Verification visuelle du frontend dans un navigateur (Chromium headless) sur les trois
  ecrans : selection d'equipe, choix de Combattant avec apercu du pool, duel resolu.
