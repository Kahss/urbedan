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
  1. Les **7 Des de pouvoir** sont tires (des identiques, 6 faces : 2 rouge, 1 bleu,
     1 jaune, 2 **epee**).
  2. La piste est parcourue creneau par creneau. A chaque creneau, le **proprietaire** du
     Personnage concerne drafte un De du pool et l'affecte a **n'importe lequel de ses 3
     Personnages** (le creneau designe qui joue, pas qui recoit).
  3. Le De drafte est utilise de l'une de ces deux facons :
     - une face **couleur** (rouge/bleu/jaune) est **stockee** en ressource sur ce
       Personnage -- sauf si **aucune** de ses Capacites n'a de case de cette couleur
       (ni de case joker), auquel cas le De est **perdu** au lieu d'etre stocke ;
     - une face **epee** est **depensee pour l'attaque de base** du Personnage : sa
       valeur d'Attaque est alors infligee aux PV adverses. Les epees ne servent qu'a
       ca et ne peuvent jamais etre stockees. Il n'y a **aucune limite** au nombre
       d'attaques par round et par Personnage (autant que d'epees qui lui sont
       assignees).
  4. Des que les Des stockes d'un Personnage payent le cout d'une de ses Capacites,
     celle-ci **s'active obligatoirement**. Si **plusieurs** Capacites sont payables en
     meme temps, le proprietaire du Personnage **choisit** laquelle s'active. Seuls les
     Des payant le cout sont defausses.
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
| `POST` | `/api/partie/draft` | `{"de_id": N, "personnage_id": "...", "usage": "stock"\|"attaque"}` | Draft du creneau courant (joueur humain) |
| `POST` | `/api/partie/choix` | `{"indice": N}` | Tranche un choix entre plusieurs Capacites payables du meme Personnage |
| `POST` | `/api/partie/ia` | — | Resout **un seul** creneau de l'IA |

`joueur_courant` indique a qui appartient le creneau courant. Le backend n'avance de
lui-meme que sur ce qui n'est pas une decision : il enchaine les rounds et saute les
creneaux devenus impossibles (pool epuise), puis s'arrete des que le creneau courant est
jouable — que ce soit celui du joueur ou celui de l'IA.

Les creneaux de l'IA sont donc resolus **un par un**, sur appel de `/api/partie/ia`, et
non par lot. C'est ce qui permet a l'interface de disposer d'un etat reel entre chaque
choix de l'IA, et donc de l'animer comme celui du joueur. Chaque route renvoie l'etat
complet, y compris `joueur_courant` : le frontend rappelle `/api/partie/ia` tant qu'il
vaut `"ia"`.

## Interface

### Selection d'equipe

Les 10 Personnages sont affiches par Initiative croissante, avec leurs couts de
capacite en clair. On clique 3 cartes, ou le bouton **Equipe aleatoire** qui remplace
la selection courante par un tirage sans remise -- pratique pour enchainer des parties
de test sans rejouer les memes trois Personnages.

### Choix de Capacite

Quand un De rend **plusieurs** Capacites d'un Personnage payables en meme temps, le draft
se met en pause : la barre de consigne affiche une ligne par Capacite, avec les Des qui
seraient defausses, et la carte concernee est cerclee de jaune (ses lignes candidates sont
surlignees). Le pool et les boutons Stocker / Attaquer sont geles jusqu'a la reponse, et le
journal garde une trace du choix propose (`⇄`) avant l'activation retenue. Cote serveur, la
cascade d'activations est reellement suspendue : le creneau n'avance pas et un second draft
est refuse.

### Journal structure

Le journal n'est pas une suite de lignes de texte : le moteur produit une structure que
l'interface rend en blocs, pour qu'on voie d'un coup d'oeil qui a joue quoi.

```
journal = [ { "numero": 2,
              "des_tires": ["bleu", "rouge", ...],
              "entrees": [ action | evenement, ... ] } ]

action    = { "genre": "action", "joueur": "humain"|"ia", "creneau": "Nitro",
              "de": "bleu"|"epee", "personnage": "Riff", "personnage_id": "riff",
              "usage": "stock"|"attaque",
              "des_stockes": 2 | "degats": 3 | "perdu": true,
              "consequences": [ ... ] }
evenement = { "genre": "evenement", "type": "fin_round"|"fin_match"|..., "texte": "..." }
```

Tout ce qu'un De declenche (activation de Capacite, PV, manipulation de Des, Attaque,
Initiative) est **imbrique dans l'action qui l'a provoque**, via `Partie._action_courante`
: `log()` ecrit dans les consequences de l'action en cours si elle existe, sinon dans les
entrees du round, sinon dans le preambule. Les call sites du moteur restent donc de
simples `partie.log(texte, type, **champs)`.

Chaque consequence porte un `type` (`capacite`, `pv`, `attaque`, `initiative`, `de`,
`de_perdu`, `choix`, `info`) qui pilote l'icone et la couleur, plus des champs structures que
l'interface prefere au texte quand ils sont presents (par exemple `joueur` / `delta` /
`avant` / `apres` pour afficher `IA -4 PV  20 -> 16`). Le champ `texte` reste toujours
rempli et lisible tel quel, ce qui garde le journal exploitable en simulation ou en debug.

**Ordre d'affichage** : le moteur produit le journal dans l'ordre chronologique, mais
l'interface le rend **du plus recent au plus ancien** — le round en cours en haut, son
entree la plus recente en premiere ligne, le preambule de mise en place tout en bas. Ce
qui vient de se passer est donc toujours visible sans scroller. Deux exceptions
volontaires : l'en-tete de round reste au-dessus de son bloc (c'est son etiquette, pas une
entree) et les **consequences** d'une action gardent leur ordre de resolution, qui se lit
comme un enchainement (`Capacite -> degats -> PV`). Le tableau `etat.journal` n'est jamais
reordonne en place : `renderJournal` copie avant d'inverser, car `actionsJournal` et le
compteur d'actions deja vues dependent de l'ordre chronologique.

### Animations

- **Transfert du De** : a chaque draft, des deux cotes, un clone du De vole du pool vers
  sa cible. En `stock`, il vient se poser a la suite des Des deja stockes du Personnage ;
  en `attaque`, il s'ecrase sur la carte et disparait (De consomme). Un `stock` qui
  s'avere `perdu` cote serveur (aucune Capacite de cette couleur) suit la meme animation
  de pose ; seul le journal et l'absence du De dans la reserve apres re-rendu signalent la
  perte. Les positions sont relevees avant tout re-rendu, et l'affichage du nouvel etat
  attend la fin de l'animation *et* de la requete.
- **Creneaux de l'IA** : `poursuivreIa()` boucle sur `/api/partie/ia` tant que
  `joueur_courant` vaut `"ia"`, avec une courte pause avant chaque pick. Le De source est
  identifie en diffant les identifiants du pool avant/apres l'appel (repli sur la couleur
  si une Capacite a retire un second De du pool), ce qui permet de partir de son
  emplacement exact. Un verrou `iaEnCours` interdit deux sequences en parallele.
- **Pulsation des Capacites** : les cartes dont une Capacite vient de se declencher
  pulsent brievement. Seules les actions ajoutees depuis le dernier rendu sont concernees
  (compteur `nbActionsVues`).
- `prefers-reduced-motion: reduce` desactive les deux : aucun clone n'est cree, la
  pulsation CSS est neutralisee, et le jeu reste entierement fonctionnel.

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
- `attaque` : degats infliges quand une **epee** est depensee pour l'attaque de base.
- `capacites` : **1 ou 2** lignes. Chaque ligne a :
  - `cout` : **1 a 3** cases. Chaque case vaut `"rouge"`, `"bleu"`, `"jaune"`, ou `null`
    pour un **joker** (n'importe quelle couleur). Les epees ne sont jamais stockees et ne
    peuvent donc jamais payer un cout. Un De d'une couleur absente de **toutes** les
    lignes de cout du Personnage (et sans joker) est perdu s'il lui est assigne.
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
  Personnage.
- **Ordre du draft** : Initiative croissante (la plus basse en premier). Une equipe aux
  Initiatives basses drafte donc tot et choisit ses couleurs avant l'adversaire : c'est un
  avantage d'equipe, compense par des valeurs d'Attaque plus faibles.
- **Usage d'un De** : determine par sa face. Une face couleur (rouge/bleu/jaune) ne peut
  qu'etre **stockee** (progression vers une Capacite) -- et est **perdue** si le
  Personnage choisi n'a aucune Capacite avec une case de cette couleur ou un joker,
  plutot que de s'accumuler indefiniment sans jamais servir ; une face **epee** ne peut
  qu'etre **depensee pour l'attaque de base** -- sans limite de nombre par round et par
  Personnage, contrairement a une version anterieure du prototype qui limitait a une
  attaque par round et par Personnage et autorisait n'importe quelle couleur a attaquer.
  Un De depense en attaque n'alimente aucune Capacite.
- **Defausse a l'activation** : seuls les Des payant le cout sont retires ; le surplus
  reste stocke (indispensable pour un Personnage a 2 lignes de Capacites).
- **Activation obligatoire, mais choix de la Capacite** : l'activation ne se refuse pas ;
  en revanche, quand **plusieurs** Capacites d'un meme Personnage sont payables au meme
  moment, c'est son **proprietaire** qui choisit laquelle s'active (Suture blessee avec un
  rouge et un bleu en reserve peut jouer `+2 PV` en ne defaussant que le bleu, ou
  `+1 PV par round ecoule` en defaussant les deux). Une seule payable s'active sans
  invite. Apres chaque activation on recommence le test (cascade bornee a 12 activations
  par De ajoute, pour se proteger d'une Capacite qui se re-alimente via `de_bonus` /
  `de_cree` / `de_vole`). L'IA tranche seule avec sa propre estimation de valeur ; le
  joueur humain est consulte et son creneau reste ouvert jusqu'a sa reponse. Sans ce
  choix, une ligne peu couteuse et sans condition rendrait inatteignable toute ligne plus
  couteuse declaree apres elle -- c'est le cas de 4 des 10 Personnages (Riff, Suture, Vex,
  Iron).
- **Choix du paiement** : le choix porte sur la **Capacite**, pas sur les Des exacts qui
  la payent. Parmi tous les paiements possibles d'une Capacite donnee, le moteur retient
  d'abord ceux qui satisfont la condition (ce qui rend `monochrome` / `polychrome`
  jouables), puis celui qui consomme les couleurs les plus abondantes de la reserve, puis
  les Des les plus anciens. Le paiement reste donc deterministe et sans invite (il n'est
  ambigu que si la reserve depasse le cout, et le paiement retenu est affiche sur le
  bouton de choix).
- **Effets de manipulation de Des** : ils ciblent automatiquement, sans invite —
  `de_bonus` prend dans le pool la couleur la plus abondante, `de_vole` / `de_defausse`
  visent le Personnage adverse qui stocke le plus de Des (egalite : le plus avance dans la
  piste) et lui prennent son De le plus ancien.
- **Modifications d'Attaque** : permanentes pour le reste du match ; l'Attaque effective
  ne descend jamais sous 0.
- **Modifications d'Initiative** : deplacements de places dans la piste, causes par un
  effet de Capacite (`initiative`). La piste est modifiee immediatement, mais la
  sequence de draft du round en cours est figee a son debut : l'effet se ressent des le
  round suivant.
- **Egalites d'Initiative** au placement initial : tranchees au hasard a la mise en place.
- **Pool epuise** : si une Capacite a consomme le De de rab (7 Des pour 6 creneaux), les
  derniers creneaux du round peuvent se retrouver sans De ; ils sont alors perdus, ce qui
  est journalise.
- **Constitution des equipes** : le joueur choisit 3 Personnages parmi les 10 (ou clique
  **Equipe aleatoire** pour en faire tirer 3 au hasard) ; l'IA en tire 3 distincts parmi
  les 7 restants. Les deux equipes sont entierement visibles.
- **PV** : pas de plafond superieur (un soin peut depasser 20 PV) ; plancher a 0.

## IA

`engine/ia.py` evalue, a chaque creneau, toutes les actions possibles pour chaque De du
pool x chacun de ses 3 Personnages -- l'usage disponible depend de la face du De -- et
retient la meilleure selon une estimation en « PV equivalents » :

- une **epee** vaut **attaquer** (la valeur d'Attaque courante du Personnage, prime
  enorme si elle acheve l'adversaire) ;
- un De **couleur** vaut **stocker** -- si le De declenche immediatement une Capacite, la
  valeur estimee de cette Capacite (la **mieux valorisee** si le De en rend plusieurs
  payables, puisque c'est celle que l'IA activera) ; sinon la **valeur marginale** de la
  progression, soit la valeur de la Capacite divisee par le nombre de Des encore
  manquants (un De vaut donc d'autant plus cher que la Capacite est proche), decotee du
  risque de ne jamais la completer ; si aucune Capacite du Personnage n'utilise cette
  couleur, la valeur est nulle -- le De serait perdu.

Le meme bareme sert d'arbitre quand plusieurs Capacites sont payables (`arbitrer_capacite`)
: l'IA active la mieux valorisee. Le paiement et la condition etant alors connus, cette
estimation-la est exacte et n'est pas decotee.

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

Etat du roster livre, sur 3000 matchs (remesures depuis que l'IA arbitre entre plusieurs
Capacites payables) : toutes les fourchettes de victoire sont comprises entre
**42,5 % et 55,5 %**, pour une duree moyenne de **3,2 rounds**.

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

Les points ci-dessous decrivent les tests menes sur la version precedente du prototype
(limite d'une attaque par round et par Personnage, aucune face epee, pas de perte de De).
Ils restent valables pour ce qu'ils couvrent (structure du journal, animations, choix de
Capacite, etc.), a l'exception du refus de « seconde attaque » mentionne ci-dessous,
desormais autorisee. Le passage aux faces epee / attaque illimitee / De perdu si aucune
Capacite ne correspond a ete revalide par : 800 matchs `generate_metagame.py` sans erreur
(y compris le cas ou `de_bonus` doit piocher dans un pool ne contenant plus que des
epees), et des appels API manuels verifiant le refus (HTTP 400) de stocker une epee, le
refus d'attaquer avec un De couleur, et le bon fonctionnement du stockage : un De dont la
couleur correspond a une Capacite du Personnage est bien stocke (et declenche la
Capacite si le cout est atteint), un De dont aucune Capacite ne correspond est journalise
comme perdu et n'apparait pas dans `des_stockes`.

- **Simulations moteur** : 3000 matchs complets IA contre IA sans erreur, avec mesure du
  taux de victoire par Personnage et de la duree des matchs.
- **API HTTP reelle** (serveur Flask demarre) : cycle complet nouvelle partie -> draft ->
  enchainement des rounds -> KO, et rejet propre (HTTP 400) d'une equipe invalide, d'un De
  inexistant et d'un Personnage hors equipe.
- **API HTTP, journal** : validation structurelle du journal (genres, champs obligatoires
  des actions, types des evenements) sur des matchs complets joues au hasard.
- **Frontend** : pilote via Chrome DevTools Protocol en headless (selection d'equipe,
  clic sur un De du pool, boutons Stocker / Attaquer, enchainement des rounds), avec
  verification visuelle par captures d'ecran de l'ecran de selection, de l'ecran de match,
  du journal et d'un De en pleine trajectoire.
- **Rendu du journal** : appel direct de `consequenceHtml` sur les 7 types de consequence
  (classe CSS et texte produits), et verification que chaque glyphe d'icone dispose bien
  d'un glyphe dans la police (comparaison de largeur avec un codepoint de zone privee).
- **Sequence de l'IA** : match complet joue depuis l'interface (12 drafts humains, 13
  creneaux d'IA sur 5 rounds) en comptant les clones animes via un `MutationObserver` :
  25 animations pour 25 actions de draft, aucun clone orphelin, aucune erreur JS. Cote
  API : refus en 400 d'un `/draft` pendant un creneau d'IA et d'un `/ia` hors creneau
  d'IA, et match complet pilote en alternant les deux routes.
- **Ordre du journal** : match joue depuis l'interface jusqu'au round 4, puis comparaison
  du DOM a l'etat serveur — blocs de round en ordre inverse, actions de chaque round en
  ordre inverse exact (creneau et cible compris), evenement de fin de round remonte en
  tete de son bloc, preambule en dernier element, `scrollTop` a 0 sur un contenu de 1618 px
  pour 649 px visibles (donc rien a scroller pour lire les dernieres lignes).
- **Choix entre plusieurs Capacites** : scenario Suture (blessee, rouge en reserve, bleu
  drafte) monte directement sur le moteur — suspension du creneau sans aucun effet
  applique, refus en 400 d'un `/draft` et d'un `/ia` pendant l'attente, refus d'un indice
  invalide sans perdre le choix, et les deux branches verifiees (`+2 PV` defausse le bleu
  et garde le rouge ; `+1 PV par round` au round 6 rend 6 PV et vide la reserve). Cote
  frontend, meme scenario pilote via CDP : invite a 2 boutons portant les Des payes, pool
  et boutons de draft geles (0 De cliquable), carte cerclee et lignes surlignees, puis
  apres le clic PV 10 -> 16, reserve videe, creneau avance et pool a nouveau cliquable.
  Cote IA, aucune invite : la Capacite la mieux valorisee est activee directement.
- **Accessibilite** : sous `prefers-reduced-motion: reduce` emule, aucun clone de De n'est
  cree, les creneaux de l'IA s'enchainent malgre tout jusqu'au tour du joueur (pas de
  blocage de la boucle) et les actions sont bien enregistrees.
- **Scenarios cibles** : deplacement d'initiative (Riff gagne 2 places), plafond de 15
  rounds avec victoire aux PV et cas d'egalite, accumulation des Des quand aucune
  Capacite n'est payable.
