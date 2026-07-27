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
data/combattants.json       Liste des 8 Combattants jouables (editable a la main)
backend/
  app.py                    Serveur Flask (API REST)
  engine/
    models.py               Glyphes, Combattants, Joueurs
    powers.py                Moteur generique de resolution des Pouvoirs
    game.py                  Orchestration d'une Partie (mise en place, duels, IA)
frontend/
  index.html / style.css / app.js   Interface (100% cliquable, sans framework)
```

## Editer / ajouter des Combattants

`data/combattants.json` peut etre modifie a la main puis rechargé automatiquement au
lancement d'une nouvelle partie (pas besoin de redemarrer le serveur). Chaque Combattant :

```json
{
  "id": "identifiant_unique",
  "nom": "Nom affiche",
  "puissance": 4,
  "degats": 3,
  "pouvoirs": [
    {
      "numero": 1,
      "description": "Texte affiche sur la carte",
      "condition": null,
      "modificateur": null,
      "effets": [ { "type": "puissance", "cible": "soi", "valeur": 2 } ]
    }
  ]
}
```

- `condition` (optionnel) : un des mots-cles Condition de `pouvoirs.csv` —
  `courage`, `riposte`, `vengeance`, `domination`, `victoire`, `defaite`, `surpuissance`.
- `modificateur` (optionnel) : un des mots-cles Modificateur —
  `patience`, `impatience`, `par_energie`, `contrecoup`.
- `effets` : liste d'effets, chacun avec un `type` :
  - `puissance` / `degats` / `vie` : necessitent `cible` (`soi` ou `adversaire`) et `valeur`
    (entier signe). `vie` modifie les PV du joueur (pas une statistique du Combattant).
  - `stop_pouvoir` : `valeur` = numero (1-3) du Pouvoir adverse a annuler.
  - `copie_pouvoir` : `valeur` = numero (1-3) du Pouvoir adverse a copier.
  - `protection` : aucun champ supplementaire.
  - `echange` : aucun champ supplementaire (echange Puissance/Degats entre les 2
    Combattants du duel).
  - `vampirisme` : `valeur` = X (reduit les PV adverses de X, gagne X PV).

Un Pouvoir peut activer plusieurs `effets` (liste), mais un seul `condition` /
`modificateur`. Le nombre de Pouvoirs actives lors d'un duel = Energie du Glyphe joue
(1 Energie -> Pouvoir 1 seul, 2 -> Pouvoirs 1 et 2, 3 -> les trois).

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
  Combattants parmi les 8 ; l'IA recoit automatiquement les 4 restants.
- **Ordre de resolution des Pouvoirs** : au sein d'un duel, J1 resout l'integralite de
  ses Pouvoirs actives (dans l'ordre 1, 2, 3) avant que J2 ne resolve les siens (et non
  un entrelacement palier par palier).
- **Stop pouvoir** : agit retroactivement si le Pouvoir cible a deja ete resolu (le cas
  lorsque J2 vise un Pouvoir de J1, deja joue), ou par anticipation sinon (J1 vise un
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
  Combattant qui possede ce Pouvoir.
- **Contrecoup** : l'effet, normalement dirige vers l'adversaire, s'applique a
  soi-meme uniquement si le Combattant remporte le duel (sinon il ne se produit pas).
- **Copie pouvoir** : copie la definition statique du Pouvoir adverse (effets,
  condition, modificateur) et l'execute du point de vue du copieur (`soi` = copieur,
  `adversaire` = adversaire du copieur), que le Pouvoir source ait ete lui-meme active ou
  non par son proprietaire. Limitation POC : copier un Pouvoir conditionne par l'issue du
  duel (Victoire/Defaite/Surpuissance) ou par Contrecoup n'est pas supporte (aucun des 8
  Combattants fournis ne le necessite).
- **Mot-cle "Attaque"** (`pouvoirs.csv`) : `game.md` ne definit que les statistiques
  Puissance et Degats pour un Combattant (pas d'"Attaque" separee). Le mot-cle
  "+/- Attaque" est donc traite comme un synonyme de "+/- Puissance".
- **Double victoire** (egalite de Puissance) : les deux Combattants remportent le duel et
  infligent chacun leurs Degats ; le joueur J2 du duel devient J1 du duel suivant (et
  inversement), conformement a `game.md`.
- **Equipe visible** : le roster complet (les 4 Combattants, utilises ou non) de chaque
  joueur est visible par l'autre pendant toute la partie ; seule la main de Glyphes de
  l'IA reste cachee (le nombre de cartes restantes est visible, pas leur contenu) jusqu'a
  ce qu'elle en joue une.

## IA

L'IA choisit aleatoirement un Combattant disponible dans son equipe, puis un Glyphe
aleatoire dans sa main, a chaque duel.

## Tests effectues

- Simulation de 30 parties completes en choix aleatoires via le moteur Python (sans
  crash).
- Simulation d'une partie complete via l'API HTTP reelle (serveur Flask demarre),
  verifiant le cycle choix Combattant -> choix Glyphe -> resolution -> duel suivant ->
  fin de partie, ainsi que le rejet propre (HTTP 400) d'une action invalide.
- Scenarios cibles verifiant individuellement : Protection (retroactive + blocage),
  Stop pouvoir (retroactif), Contrecoup (redirection sur victoire), Surpuissance.
- Verification manuelle du frontend (HTML/CSS/JS) par lecture de code ; a tester
  visuellement dans un navigateur avant mise en usage reel.
