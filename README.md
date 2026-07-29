# Urban Eredan — Prototype

Prototype jouable en solo (vs IA) du jeu de societe Urban Eredan (`game.md`), avec un
backend Python (moteur de regles + IA) et un frontend web (HTML/CSS/JS, jouable
uniquement au clic).

## Lancer le jeu

Un environnement virtuel Python existe deja dans `venv/`. Depuis la racine du projet :

```
venv\Scripts\python.exe -m pip install -r backend\requirements.txt
venv\Scripts\python.exe backend\app.py
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
    models.py               Glyphes, Combattants, Joueurs
    powers.py                Moteur generique de resolution des Pouvoirs
    ia.py                    Heuristique de choix de l'IA (Combattant + Glyphe)
    game.py                  Orchestration d'une Partie (mise en place, duels, IA)
frontend/
  index.html / style.css / app.js   Interface (100% cliquable, sans framework)
```

## Editer / ajouter des Combattants

`data/combattants.json` peut etre modifie a la main puis rechargé automatiquement au
lancement d'une nouvelle partie (pas besoin de redemarrer le serveur). Chaque Combattant
ne possede plus qu'un seul Pouvoir :

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
    "energie_min": 1,
    "effets": [ { "type": "puissance", "cible": "soi", "valeur": 2 } ]
  }
}
```

- `energie_min` (optionnel, defaut 0) : cout minimum en Energie pour activer le Pouvoir,
  note "X+" — le Pouvoir s'active des lors que l'Energie du Glyphe joue est superieure ou
  egale a `energie_min` (`0` ou absent = Pouvoir toujours actif, meme avec un Glyphe
  d'Energie 0).
- `condition` (optionnel) : un des mots-cles Condition de `pouvoirs.csv` —
  `courage`, `riposte`, `vengeance`, `domination`, `victoire`, `defaite`, `surpuissance`.
- `modificateur` (optionnel) : un des mots-cles Modificateur —
  `patience`, `impatience`, `par_energie`, `par_energie_adverse`, `par_energie_en_jeu`,
  `contrecoup`. `par_energie` multiplie la valeur de l'effet par l'Energie jouee par le
  Combattant lui-meme (ex : "+1 Puissance / Energie") ; `par_energie_adverse` multiplie
  par l'Energie jouee par l'adversaire ce duel-ci ; `par_energie_en_jeu` multiplie par la
  somme des deux Energies jouees (soi + adversaire). Dans tous les cas, combine a
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

**L'Energie du Glyphe joue determine si l'unique Pouvoir du Combattant s'active**, en le
comparant a son seuil `energie_min` : Energie jouee >= `energie_min` -> le Pouvoir
s'active (avec, le cas echeant, une valeur multipliee par cette Energie via
`par_energie`) ; sinon, il reste inactif. Un Combattant n'a donc jamais plus d'un Pouvoir
actif par duel (hors effet de Copie pouvoir). Concevoir un personnage revient a choisir
un seul Pouvoir, son cout minimum en Energie (0 = toujours disponible, 3 = ne
s'active qu'en sacrifiant toute la Puissance du Glyphe 0/3) et, eventuellement, un
scaling par Energie jouee au-dela de ce seuil.

## Detail du calcul de Puissance / Degats

A la resolution d'un duel, l'API renvoie pour chaque Combattant le detail complet du
calcul (`puissance_txt`, `degats_txt`, affiches sur la carte du duel resolu), sous la
forme `total = X (base) + Y (glyphe) + Z (Pouvoir N Nom) ...`. Chaque contribution
(base, Glyphe, chaque Pouvoir ayant modifie la valeur, y compris un Echange ou une copie
de pouvoir) apparait comme une ligne separee, dans l'ordre ou elle a ete appliquee. Cela
permet de verifier precisement d'ou vient un nombre qui semblerait incoherent au premier
abord (ex : un Combattant dont la Puissance ne semble pas inclure son Glyphe, alors
qu'un Echange ulterieur la lui a simplement retiree).

## Hypotheses et choix d'implementation

Certaines regles de `game.md` / `pouvoirs.csv` laissaient place a interpretation ; les
choix suivants ont ete valides ou tranches avec l'utilisateur avant developpement :

- **Selection d'equipe** : avant chaque partie, le joueur choisit manuellement ses 4
  Combattants parmi tous ceux disponibles (20 fournis) ; l'IA tire au hasard 4
  Combattants distincts parmi ceux restants.
- **Un seul Pouvoir par Combattant** : chaque Combattant ne possede plus qu'un unique
  Pouvoir, actif des lors que l'Energie du Glyphe joue atteint son seuil `energie_min`
  (note "X+"). **Ordre de resolution** : au sein d'un duel, J1 resout son Pouvoir (s'il
  est actif) avant que J2 ne resolve le sien.
- **Stop pouvoir et Copie pouvoir sont generiques** : ils visent toujours l'unique
  Pouvoir de l'adversaire, s'il est actif (Energie jouee >= son seuil `energie_min`). Si
  l'adversaire n'a pas atteint ce seuil (Pouvoir inactif), il n'y a rien a annuler ni a
  copier.
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
- **Par energie** : multiplie la valeur de l'effet par l'Energie du Glyphe joue par le
  Combattant qui possede ce Pouvoir (ex : Echo, Cobra, Iron, Riff). Combine a
  `energie_min`, cela permet un Pouvoir qui necessite un minimum d'Energie pour
  s'activer, et dont l'effet croit ensuite avec l'Energie investie au-dela de ce seuil.
- **Par energie adverse** : multiplie la valeur de l'effet par l'Energie jouee par
  l'adversaire ce duel-ci, independamment de la propre Energie du Combattant (ex :
  Mirage, qui retourne l'investissement en Energie de l'adversaire contre lui).
- **Par energie en jeu** : multiplie la valeur de l'effet par la somme des deux Energies
  jouees ce duel-ci (la sienne et celle de l'adversaire) (ex : Surge, qui se nourrit du
  chaos total du duel, peu importe qui l'a genere).
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
  joueur est visible par l'autre pendant toute la partie ; la main de Glyphes de l'IA
  (valeurs et nombre de cartes) reste totalement masquee jusqu'a la resolution du duel.
- **Main de 2 Glyphes par manche** : chaque joueur pioche un premier Glyphe a la mise en
  place de la partie (main de depart), puis un Glyphe supplementaire au debut de chaque
  manche (duel), dans le deck commun (20 cartes, 5 exemplaires de chacun des 4 types de
  Glyphe, partage par les deux joueurs, jamais reconstitue en cours de partie). Il a
  donc 2 Glyphes disponibles pour choisir lequel associer au Combattant qu'il joue ce
  duel-ci ; l'autre reste en main pour la manche suivante. Le joueur humain voit sa
  propre main avant de choisir son Combattant et son Glyphe ; celle de l'IA reste cachee
  jusqu'a la resolution du duel.
- **Compteur de Glyphes restants** : l'interface rappelle, pour chacun des 4 types de
  Glyphe, combien d'exemplaires restent potentiellement disponibles (sur les 5 de
  depart), en comptant uniquement ceux deja joues (reveles en resolution de duel) — les
  Glyphes actuellement dans une main (y compris celle, cachee, de l'IA) sont donc
  toujours comptes comme "restants", puisque leur type n'est pas encore connu de
  l'autre joueur.

## IA

L'IA (`engine/ia.py`) choisit, parmi ses Combattants disponibles et ses Glyphes en main,
la combinaison qui maximise une estimation de la Puissance totale du duel (en cas
d'egalite : les Degats, puis la Vie), plutot qu'un tirage purement aleatoire. Cette
estimation ne compte que ce qui est certain au moment du choix :
- Courage / Riposte / Vengeance / Domination sont evalues immediatement (role du duel,
  PV courants) ; Victoire / Defaite / Surpuissance / Contrecoup dependent de l'issue du
  duel (inconnue au moment du choix) et ne sont donc jamais comptes.
- Patience / Impatience / Par energie sont calcules directement ; Par energie adverse /
  Par energie en jeu utilisent l'Energie moyenne d'un Glyphe pioche au hasard (1,5),
  l'Energie reelle de l'adversaire etant inconnue avant la resolution.
- Stop pouvoir / Copie pouvoir / Protection / Echange dependent trop du Combattant et du
  Glyphe adverses (inconnus) pour etre estimes utilement : ils ne modifient pas le
  score.

Les egalites de score sont tranchees au hasard, pour eviter un jeu totalement
previsible.

## Tests effectues

- Simulation de 30 parties completes en choix aleatoires via le moteur Python (sans
  crash).
- Simulation d'une partie complete via l'API HTTP reelle (serveur Flask demarre),
  verifiant le cycle pioche Glyphe -> choix Combattant (resolution automatique une fois
  les deux choisis) -> duel suivant -> fin de partie, ainsi que le rejet propre
  (HTTP 400) d'une action invalide.
- Scenarios cibles verifiant individuellement : Protection (retroactive + blocage),
  Stop pouvoir (retroactif), Contrecoup (redirection sur victoire), Surpuissance,
  Patience/Impatience (base duel courant), regle "Energie = quel Pouvoir s'active" (et
  non plus combien), genericite de Stop pouvoir et Copie pouvoir (y compris le cas
  "l'adversaire n'a active aucun Pouvoir").
- Verification manuelle du frontend (HTML/CSS/JS) par lecture de code ; a tester
  visuellement dans un navigateur avant mise en usage reel.
