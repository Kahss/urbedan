# Urban Eredan — Eredice (prototype)

Prototype jouable en solo (vs IA) de la version **Eredice** d'Urban Eredan
(`versions/eredice.md`) : deux equipes de 3 Personnages s'affrontent en 3v3, et toute la
partie se joue autour d'un **draft de Des de pouvoir**. Backend Python (moteur de regles
+ IA), frontend web sans framework, jouable uniquement au clic.

## Lancer le jeu

Le projet est gere par `uv` (cf. `pyproject.toml`) :

```
uv run backend/app.py
```

Ou avec l'environnement virtuel existant :

```
.venv/bin/python backend/app.py
```

Puis ouvrir http://127.0.0.1:5000/.

Le serveur Flask sert a la fois l'API (`/api/...`) et les fichiers statiques du frontend.
Une seule partie est active a la fois (etat en memoire, adapte a un usage solo local).

## Regles implementees

- Chaque joueur demarre a **20 PV**. Le match s'arrete des qu'un joueur tombe a 0.
- Les 6 Personnages des deux equipes forment une **piste d'initiative** commune, triee
  par Initiative **croissante** : l'Initiative la plus basse drafte en premier. Les
  valeurs d'Initiative ne servent qu'a ce placement initial ; ensuite, seules les
  **places** comptent (un effet `initiative` deplace un Personnage de N places).
- A chaque round :
  1. Les **7 Des de pouvoir** sont tires (des identiques, faces rouge/rouge/bleu/bleu/
     jaune/jaune : un tirage est donc uniforme sur les 3 couleurs).
  2. La piste est parcourue creneau par creneau. A chaque creneau, le **proprietaire** du
     Personnage concerne drafte un De du pool et l'affecte a **n'importe lequel de ses 3
     Personnages** (le creneau designe qui joue, pas qui recoit).
  3. Le De est soit **stocke** en ressource sur ce Personnage, soit **depense pour son
     attaque de base** : sa valeur d'Attaque est alors infligee aux PV adverses. Une
     seule attaque par round et par Personnage ; aucune contrainte de couleur.
  4. Des que les Des stockes d'un Personnage payent le cout d'une de ses Capacites,
     celle-ci **s'active obligatoirement**. Seuls les Des payant le cout sont defausses.
  5. Apres les 6 creneaux, le De non drafte est defausse et un nouveau round commence.
- Un plafond de **15 rounds** sert de garde-fou (victoire aux PV) : la spec ne prevoit
  qu'une fin par KO, mais deux equipes tres defensives pourraient boucler indefiniment.

## Structure du projet

```
data/personnages.json        Les 10 Personnages jouables (editable a la main)
pouvoirs.csv                 Liste des mots-cles Effet / Condition / Multiplicateur
backend/
  app.py                     Serveur Flask (API REST)
  engine/
    models.py                Des de pouvoir, Personnages, Joueurs
    capacites.py             Resolution des Capacites (paiement, conditions, effets)
    game.py                  Orchestration d'un match (piste, rounds, draft, fin)
    ia.py                    Heuristique de draft de l'IA
frontend/
  index.html / style.css / app.js   Interface (100% cliquable, sans framework)
generate_metagame.py         Simulation IA vs IA et statistiques d'equilibrage
versions/                    Specifications des variantes du jeu
```

## API

| Methode | Route | Corps | Role |
| --- | --- | --- | --- |
| `GET` | `/api/personnages` | — | Les 10 Personnages disponibles |
| `POST` | `/api/partie` | `{"equipe": [id, id, id]}` | Nouvelle partie (l'IA tire 3 Personnages parmi les 7 restants) |
| `GET` | `/api/partie` | — | Etat courant |
| `POST` | `/api/partie/draft` | `{"de_id": N, "personnage_id": "...", "usage": "stock"\|"attaque"}` | Draft du creneau courant |

Apres chaque action humaine, le backend joue automatiquement tous les creneaux de l'IA
et enchaine les rounds jusqu'a ce que ce soit de nouveau au joueur d'agir : l'etat
renvoye est donc toujours pret pour la prochaine decision humaine.

## Editer / ajouter des Personnages

`data/personnages.json` est relu a chaque nouvelle partie (pas besoin de redemarrer le
serveur).

```json
{
  "id": "identifiant_unique",
  "nom": "Nom affiche",
  "archetype": "narratif, non lu par le moteur",
  "description": "narratif, non lu par le moteur",
  "initiative": 5,
  "attaque": 2,
  "capacites": [
    {
      "description": "Texte affiche sur la carte",
      "cout": ["rouge", null],
      "condition": null,
      "multiplicateur": null,
      "effets": [ { "type": "vampirisme", "valeur": 3 } ]
    }
  ]
}
```

- `initiative` : placement initial sur la piste (la plus **basse** drafte en premier).
- `attaque` : degats infliges quand un De est depense pour l'attaque de base.
- `capacites` : **1 ou 2** lignes. Chaque ligne a :
  - `cout` : **1 a 3** cases. Chaque case vaut `"rouge"`, `"bleu"`, `"jaune"`, ou `null`
    pour un **joker** (n'importe quelle couleur).
  - `condition` (optionnelle), `multiplicateur` (optionnel) : mots-cles de
    `pouvoirs.csv`.
  - `effets` : liste d'effets, chacun avec un `type` de `pouvoirs.csv`.

Un cout en **jokers purs** n'impose aucune contrainte de couleur : a valeur egale, il est
nettement plus fort qu'un cout colore. C'est le principal levier d'equilibrage, avec la
valeur par De et l'Attaque de base.

## Hypotheses et choix d'implementation

Les points laisses ouverts par `versions/eredice.md` ont ete tranches comme suit (valides
avec l'utilisateur avant developpement) :

- **Draft libre** : le creneau de la piste designe le **joueur** qui drafte, pas le
  Personnage qui recoit. Le joueur peut empiler ses 3 Des du round sur un seul
  Personnage. La regle « une seule attaque par round et par Personnage » devient donc
  reellement contraignante.
- **Ordre du draft** : Initiative croissante (la plus basse en premier). Une equipe aux
  Initiatives basses drafte donc tot et choisit ses couleurs avant l'adversaire : c'est un
  avantage d'equipe, compense par des valeurs d'Attaque plus faibles.
- **Usage d'un De** : choix exclusif entre stocker (progression vers une Capacite) et
  depenser pour l'attaque de base. Un De depense en attaque n'alimente aucune Capacite.
- **Defausse a l'activation** : seuls les Des payant le cout sont retires ; le surplus
  reste stocke (indispensable pour un Personnage a 2 lignes de Capacites).
- **Activation obligatoire et ordre de test** : un Personnage teste ses Capacites dans
  leur **ordre de declaration** ; la premiere payable s'active, puis on recommence
  (cascade bornee a 12 activations par De ajoute, pour se proteger d'une Capacite qui se
  re-alimente via `de_bonus` / `de_cree` / `de_vole`). Consequence de design : une ligne
  peu couteuse et sans condition rend inatteignable toute ligne plus couteuse declaree
  apres elle.
- **Choix du paiement** : parmi tous les paiements possibles, le moteur retient d'abord
  ceux qui satisfont la condition (ce qui rend `monochrome` / `polychrome` jouables), puis
  celui qui consomme les couleurs les plus abondantes de la reserve, puis les Des les plus
  anciens. Le paiement est deterministe : aucune invite supplementaire au joueur.
- **Effets de manipulation de Des** : ils ciblent automatiquement, sans invite —
  `de_bonus` prend dans le pool la couleur la plus abondante, `de_vole` / `de_defausse`
  visent le Personnage adverse qui stocke le plus de Des (egalite : le plus avance dans la
  piste) et lui prennent son De le plus ancien.
- **Modifications d'Attaque** : permanentes pour le reste du match ; l'Attaque effective
  ne descend jamais sous 0.
- **Modifications d'Initiative** : deplacements de places dans la piste. La piste est
  modifiee immediatement, mais la sequence de draft du round en cours est figee a son
  debut : l'effet se ressent des le round suivant.
- **Egalites d'Initiative** au placement initial : tranchees au hasard a la mise en place.
- **Pool epuise** : si une Capacite a consomme le De de rab (7 Des pour 6 creneaux), les
  derniers creneaux du round peuvent se retrouver sans De ; ils sont alors perdus, ce qui
  est journalise.
- **Constitution des equipes** : le joueur choisit 3 Personnages parmi les 10 ; l'IA en
  tire 3 distincts parmi les 7 restants. Les deux equipes sont entierement visibles.
- **PV** : pas de plafond superieur (un soin peut depasser 20 PV) ; plancher a 0.

## IA

`engine/ia.py` evalue, a chaque creneau, toutes les actions possibles (chaque De du pool x
chacun de ses 3 Personnages x stocker/attaquer) et retient la meilleure selon une
estimation en « PV equivalents » :

- **attaquer** vaut la valeur d'Attaque courante du Personnage (prime enorme si elle
  acheve l'adversaire) ;
- **stocker** vaut, si le De declenche immediatement une Capacite, la valeur estimee de
  cette Capacite ; sinon la **valeur marginale** de la progression, soit la valeur de la
  Capacite divisee par le nombre de Des encore manquants (un De vaut donc d'autant plus
  cher que la Capacite est proche), decotee du risque de ne jamais la completer.

Les conditions d'etat (`vengeance`, `domination`, `blesse`, position dans la piste) sont
evaluees immediatement ; `monochrome` / `polychrome` dependent du paiement retenu et sont
seulement decotees. Les egalites de score sont tranchees au hasard.

## Equilibrage

`generate_metagame.py` simule des matchs IA contre IA (equipes tirees au hasard dans tout
le roster) et mesure, pour chaque Personnage, le pourcentage de matchs remportes par
**l'equipe dont il fait partie** :

```
python generate_metagame.py -n 3000
```

Etat du roster livre, sur 3000 matchs : toutes les fourchettes de victoire sont comprises
entre **42,8 % et 55,5 %**, pour une duree moyenne de **3,2 rounds**.

Deux observations utiles pour la suite :

- **Duree des matchs.** A 20 PV, avec 3 Des par joueur et par round et des Capacites
  rentables (~2,5 PV par De), un match dure structurellement 3 a 4 rounds. Allonger les
  parties suppose soit de monter les PV de depart, soit de baisser d'un tiers toutes les
  valeurs de degats/soins et d'Attaque — ce dernier point rendant les Capacites a 3 Des
  plus difficiles a rentabiliser.
- **Sensibilite de l'equilibrage.** L'IA etant gloutonne, un seul point de degats sur une
  Capacite peut faire basculer son comportement (elle canalise alors tous les Des d'une
  couleur vers un Personnage) et deplacer son taux de victoire de 20 points. Les valeurs
  livrees ont ete calees sur ce comportement : elles sont a revalider si l'heuristique de
  l'IA change.

## Tests effectues

- **Simulations moteur** : 3000 matchs complets IA contre IA sans erreur, avec mesure du
  taux de victoire par Personnage et de la duree des matchs.
- **API HTTP reelle** (serveur Flask demarre) : cycle complet nouvelle partie -> draft ->
  enchainement des rounds -> KO, et rejet propre (HTTP 400) d'une equipe invalide, d'un De
  inexistant, d'un Personnage hors equipe et d'une seconde attaque du meme Personnage dans
  le round.
- **Frontend** : pilote via Chrome DevTools Protocol en headless (selection d'equipe,
  clic sur un De du pool, boutons Stocker / Attaquer, enchainement des rounds), avec
  verification visuelle par captures d'ecran de l'ecran de selection et de l'ecran de
  match.
- **Scenarios cibles** : deplacement d'initiative (Riff gagne 2 places), plafond de 15
  rounds avec victoire aux PV et cas d'egalite, refus de la seconde attaque d'un
  Personnage dans le meme round, accumulation des Des quand aucune Capacite n'est payable.
