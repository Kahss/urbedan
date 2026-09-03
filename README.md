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
    models.py               Cartes Puissance, Combattants, Joueurs
    powers.py                Moteur generique de resolution des Pouvoirs
    ia.py                    Heuristique de choix de l'IA (Combattant + pioche stop ou encore)
    game.py                  Orchestration d'une Partie (mise en place, duels, IA)
frontend/
  index.html / style.css / app.js   Interface (100% cliquable, sans framework)
```

## Editer / ajouter des Combattants

`data/combattants.json` peut etre modifie a la main puis rechargé automatiquement au
lancement d'une nouvelle partie (pas besoin de redemarrer le serveur). Chaque Combattant
ne possede plus qu'un seul Pouvoir, toujours actif :

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

- `condition` (optionnel) : un des mots-cles Condition de `pouvoirs.csv` —
  `courage`, `riposte`, `vengeance`, `domination`, `victoire`, `defaite`, `surpuissance`.
- `modificateur` (optionnel) : un des mots-cles Modificateur —
  `patience`, `impatience`, `par_carte`, `par_carte_adverse`, `par_carte_en_jeu`,
  `contrecoup`. `par_carte` multiplie la valeur de l'effet par le nombre de Cartes
  Puissance piochees par le Combattant lui-meme pendant la phase de pioche du duel (ex :
  "+1 Puissance / carte piochee") ; `par_carte_adverse` multiplie par le nombre de cartes
  piochees par l'adversaire ce duel-ci ; `par_carte_en_jeu` multiplie par la somme des
  deux (soi + adversaire). Ces trois modificateurs sont plafonnes par `plafond_cartes`
  (optionnel, defaut 3) : le nombre de cartes compte est limite a ce plafond, pour garder
  ces Pouvoirs equilibres malgre le nombre de cartes potentiellement piochees.
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

**Le Pouvoir d'un Combattant est toujours actif** (version "stop ou encore" : il n'y a
plus d'Energie determinant son activation). Concevoir un personnage revient a choisir un
seul Pouvoir et, eventuellement, un scaling par nombre de cartes piochees (`par_carte*`,
plafonne par `plafond_cartes`).

## Detail du calcul de Puissance / Degats

A la resolution d'un duel, l'API renvoie pour chaque Combattant le detail complet du
calcul (`puissance_txt`, `degats_txt`, affiches sur la carte du duel resolu), sous la
forme `total = X (base) + Y (cartes piochees) + Z (Pouvoir N Nom) ...`. Chaque
contribution (base, cartes piochees, chaque Pouvoir ayant modifie la valeur, y compris
un Echange ou une copie de pouvoir) apparait comme une ligne separee, dans l'ordre ou
elle a ete appliquee. Cela permet de verifier precisement d'ou vient un nombre qui
semblerait incoherent au premier abord (ex : un Combattant dont la Puissance des cartes
piochees est a 0 alors qu'il a beaucoup pioche, parce qu'il a "bust" avec 3 Malus ou
plus).

## Hypotheses et choix d'implementation

Cette version ("stop ou encore", voir `versions/stop_ou_encore.md`) remplace
integralement le systeme precedent de Glyphes/Energie par une phase de pioche a tour de
role. Certaines regles laissaient place a interpretation ; les choix suivants ont ete
valides ou tranches avec l'utilisateur avant developpement :

- **Selection d'equipe** : avant chaque partie, le joueur choisit manuellement ses 4
  Combattants parmi tous ceux disponibles (20 fournis) ; l'IA tire au hasard 4
  Combattants distincts parmi ceux restants.
- **Un seul Pouvoir par Combattant, toujours actif** : chaque Combattant ne possede
  plus qu'un unique Pouvoir, qui s'applique systematiquement (il n'y a plus d'Energie
  determinant son activation). **Ordre de resolution** : au sein d'un duel, J1 resout
  son Pouvoir avant que J2 ne resolve le sien.
- **Bust (Malus total >= 3)** : seule la Puissance apportee par les cartes piochees ce
  duel-ci est annulee ; la Puissance de base du Combattant est conservee. Cette regle ne
  s'applique qu'a l'addition directe des cartes : un Pouvoir `par_carte*` du Combattant
  continue de scaler sur le nombre de cartes piochees (qui reste connu), meme apres un
  bust — ce sont deux mecaniques independantes (l'une additive sur les valeurs des
  cartes, l'autre sur leur nombre).
- **Tas de Cartes Puissance remelange a chaque duel** : 20 cartes (3 Destin, 7 Chance, 7
  Peripetie, 3 Malheur), sans lien entre les duels. Si le tas est epuise en cours de
  duel (les deux joueurs ont beaucoup pioche), il n'est plus possible de piocher — seul
  "s'arreter" reste disponible.
- **Visibilite pendant la pioche** : les cartes de l'adversaire restent cachees jusqu'a
  la resolution du duel ; seuls le nombre de cartes deja piochees par l'adversaire et le
  fait qu'il se soit arrete ou non sont visibles en temps reel (`etat.pioche`).
- **Stop pouvoir et Copie pouvoir sont generiques** : ils visent toujours l'unique
  Pouvoir de l'adversaire (toujours actif).
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
- **Par carte** : multiplie la valeur de l'effet par le nombre de Cartes Puissance
  piochees par le Combattant qui possede ce Pouvoir ce duel-ci (ex : Echo, Cobra, Iron,
  Riff, Loup), plafonne par `plafond_cartes` (defaut 3, choisi pour rester dans l'ordre
  de grandeur de l'ancien maximum d'Energie — a ajuster empiriquement, voir
  `generate_metagame.py`).
- **Par carte adverse** : multiplie la valeur de l'effet par le nombre de cartes
  piochees par l'adversaire ce duel-ci (ex : Mirage, qui retourne l'investissement de
  l'adversaire contre lui), meme plafond.
- **Par carte en jeu** : multiplie la valeur de l'effet par la somme des deux nombres de
  cartes piochees ce duel-ci (la sienne et celle de l'adversaire) (ex : Surge, qui se
  nourrit du chaos total du duel), meme plafond applique a la somme.
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
  joueur est visible par l'autre pendant toute la partie.

## IA

L'IA (`engine/ia.py`) intervient a deux moments :
- **Choix du Combattant** (`choisir_combattant`) : choisit, parmi ses Combattants
  disponibles, celui qui maximise une estimation de la Puissance totale du duel a venir
  (en cas d'egalite : les Degats, puis la Vie), plutot qu'un tirage purement aleatoire.
  Courage / Riposte / Vengeance / Domination sont evalues immediatement (role du duel,
  PV courants) ; Victoire / Defaite / Surpuissance / Contrecoup dependent de l'issue du
  duel et ne sont jamais comptes ; les modificateurs `par_carte*` sont estimes avec un
  nombre moyen de cartes (`NB_CARTES_MOYEN_ESTIME`), le nombre reel de cartes qui seront
  piochees n'etant pas encore connu au moment de choisir son Combattant.
- **Decision de pioche** (`decider_piocher_ou_arreter`) : a chaque tour, calcule
  l'esperance de gain d'une carte supplementaire a partir de la composition exacte du
  tas restant (connue, puisque c'est un jeu de cartes fini) : probabilite de "bust"
  (Malus total qui atteindrait 3) ponderee par la perte de la Puissance des cartes deja
  accumulee, contre le gain moyen d'une carte qui ne ferait pas bust. Pioche tant que
  cette esperance est positive, s'arrete sinon.

Les egalites de score (choix du Combattant) sont tranchees au hasard, pour eviter un jeu
totalement previsible.

## Tests effectues

- Simulation de 200 parties completes en choix aleatoires (Combattant + piocher/
  s'arreter) via le moteur Python (sans crash, `garde_fou` anti-boucle-infinie).
- Simulation d'une partie complete via l'API HTTP reelle (serveur Flask demarre),
  verifiant le cycle choix Combattant (resolution IA automatique) -> pioche a tour de
  role (piocher/s'arreter, y compris bust force et epuisement du tas) -> resolution du
  duel -> duel suivant -> fin de partie, ainsi que le rejet propre (HTTP 400) d'une
  action invalide ou hors phase.
- Scenarios cibles verifiant individuellement : bust (Malus >= 3 -> Puissance des cartes
  annulee, base conservee, Pouvoir `par_carte` toujours applique), egalite de Puissance
  (double victoire), tas de Cartes Puissance epuise en cours de duel (piocher devient
  impossible, HTTP 400), plafond `plafond_cartes` sur `par_carte`/`par_carte_adverse`/
  `par_carte_en_jeu`.
- `generate_metagame.py` (IA contre IA, avec la meme heuristique de pioche des deux
  cotes) execute sans erreur ; premiere lecture du taux de victoire par Combattant
  montrant les personnages a Pouvoir `par_carte*` (Echo, Riff, Cobra) en tete — signal a
  surveiller pour ajuster `plafond_cartes` a la baisse si confirme sur un plus grand
  nombre de parties.
- Verification manuelle du frontend (HTML/CSS/JS) par lecture de code ; a tester
  visuellement dans un navigateur avant mise en usage reel.
