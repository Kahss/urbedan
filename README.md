# Urban Eredan — Prototype (version « cartes Bataille »)

Prototype jouable en solo (vs IA) du jeu de societe Urban Eredan (`game.md`), dans la
variante decrite par `versions/battles.md` : un duel ne se resout plus par une comparaison
de Puissance, mais en remportant **3 batailles** revelees une par une depuis deux pioches
communes. Backend Python (moteur de regles + IA), frontend web (HTML/CSS/JS, jouable
uniquement au clic).

## Ce qui change par rapport a la version de reference

- Les cartes **Glyphes**, l'**Energie** et les **Pouvoirs** disparaissent.
- Un Combattant n'a plus de Puissance : il porte trois caracteristiques, **Force**
  (rouge), **Dexterite** (vert) et **Sagesse** (bleu), chacune de 0 a 5, plus ses Degats.
- Un deck de **20 cartes Bataille**, coupe en **2 pioches de 10** au centre de la table,
  sert a tous les duels de la partie. Le recto porte la condition qui designe le vainqueur
  de la bataille ; le verso ne montre qu'**une couleur**, choisie parmi les
  caracteristiques que la condition utilise.
- Le premier Combattant a remporter **3 batailles** remporte le duel et inflige ses
  Degats. Une bataille que la condition ne tranche pas est **nulle** : personne ne marque.

## Lancer le jeu

Le projet est gere avec [uv](https://docs.astral.sh/uv/) :

```
uv run python backend/app.py
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
    batailles.py            Les 20 cartes Bataille, leur resolution et les 2 pioches
    models.py               Combattants, Joueurs
    ia.py                   Heuristique de l'IA (Combattant + choix de pioche)
    game.py                 Orchestration d'une Partie (mise en place, duels, batailles)
frontend/
  index.html / style.css / app.js   Interface (100% cliquable, sans framework)
generate_metagame.py        Simulation IA contre IA : % de victoire par Combattant
```

## Les 20 cartes Bataille

Definies dans `backend/engine/batailles.py` (`MODELES`), avec leur nom, leur condition et
la couleur de leur dos. Le deck est structure de facon symetrique : chaque caracteristique
est la caracteristique principale de 6 cartes, et les 2 dernieres cartes lisent les trois
caracteristiques.

| Type de condition | Exemplaires | Exemple |
| --- | --- | --- |
| `max` : la caracteristique la plus haute l'emporte | 3 par caracteristique | Bras de fer — Force la plus haute |
| `min` : la plus basse l'emporte | 1 par caracteristique | Passage etroit — Force la plus basse |
| `somme` : la somme de deux caracteristiques la plus haute | 1 par caracteristique | Escalade sauvage — Force + Dexterite la plus haute |
| `max_departage` : la plus haute, puis une seconde caracteristique en cas d'egalite | 1 par caracteristique | Poigne et sang-froid — Force la plus haute ; a egalite, Sagesse |
| `total` : le total des trois le plus haut | 1 | Melee generale |
| `meilleure` : la meilleure des trois la plus haute | 1 | Coup d'eclat |

Les caracteristiques tournent en cycle (Force → Dexterite → Sagesse → Force) pour les
sommes et les departages, de sorte que les trois groupes de 6 cartes soient rigoureusement
equivalents : aucune caracteristique n'est structurellement meilleure qu'une autre.

**Le dos** d'une carte est une des couleurs que sa condition lit, fixee une fois pour
toutes (comme une carte imprimee). Les dos se repartissent en 6 rouges, 7 verts et
7 bleus — 20 n'etant pas divisible par 3, les deux cartes globales rompent d'un cheveu la
symetrie des dos, jamais celle des conditions. Un dos rouge cache ainsi 3 fois « Force la
plus haute », mais aussi « Force la plus basse », « Sagesse + Force la plus haute » et
« Dexterite la plus haute, a egalite Force » : l'indice oriente sans jamais garantir.

## Editer / ajouter des Combattants

`data/combattants.json` peut etre modifie a la main puis est recharge automatiquement au
lancement d'une nouvelle partie (pas besoin de redemarrer le serveur).

```json
{
  "id": "identifiant_unique",
  "nom": "Nom affiche",
  "archetype": "texte narratif, ignore par le moteur",
  "description": "texte narratif, ignore par le moteur",
  "force": 5,
  "dexterite": 1,
  "sagesse": 3,
  "degats": 3,
  "pouvoir": { "...": "conserve en donnees, ignore par cette version" }
}
```

- `force` / `dexterite` / `sagesse` : entiers de 0 a 5 (le moteur refuse toute valeur hors
  de cet intervalle au chargement).
- `degats` : PV retires a l'adversaire quand le Combattant remporte son duel.
- `pouvoir` : conserve tel quel pour une version ulterieure ; ni le moteur ni le frontend
  ne le lisent.

### Equilibrer un Combattant

Le total des trois caracteristiques mesure la frequence a laquelle un Combattant gagne ses
duels ; les **Degats** compensent cette frequence. Le roster fourni se tient entre 8 et 10 :
en dessous, un Combattant perd trop souvent pour que ses Degats (plafonnes a 5) puissent
compenser. Deux proprietes du deck guident la repartition :

- **Les valeurs extremes valent mieux que les valeurs moyennes** : un 5 remporte les
  3 cartes « la plus haute » de sa couleur, et un 0 remporte celle « la plus basse ».
  Une ligne 5/0/4 est nettement plus solide qu'une ligne 3/3/3 de meme total.
- **Un total eleve doit se payer en Degats** : le roster fourni va de 2 Degats (pour les
  profils qui gagnent ~65 % de leurs duels) a 5 Degats (pour ceux qui en gagnent ~38 %).

Le roster fourni (22 Combattants) a ete regle de cette facon : chaque Combattant inflige
en moyenne autant de PV qu'il en subit, a 0,31 PV par duel pres (mesure par simulation sur
toutes les paires possibles).

## IA

`engine/ia.py` :

- **Choix du Combattant** : tire au hasard parmi ceux qui n'ont pas encore combattu ;
  l'IA ne contre-choisit pas le Combattant adverse.
- **Choix de la pioche** : c'est la seule decision reellement informee du duel. L'IA ne
  connait de chaque pioche que la couleur au dos de sa carte du dessus, mais elle connait
  la composition du deck et voit les cartes deja revelees : elle sait donc exactement
  quelles cartes dorment encore dans les deux pioches, sans savoir laquelle est ou. Pour
  chaque pioche, elle resout toutes les cartes encore en jeu portant cette couleur contre
  les caracteristiques des deux Combattants engages, et retient la pioche de meilleure
  esperance (+1 bataille gagnee, -1 perdue, 0 nulle). Les egalites sont tranchees au
  hasard.

Le joueur humain dispose exactement de la meme information : l'interface rappelle en
permanence quelles cartes du deck sont encore dans les pioches.

## Hypotheses et choix d'implementation

`versions/battles.md` laissait plusieurs points ouverts ; ils ont ete tranches avec
l'utilisateur avant developpement :

- **Bataille nulle** : si la condition ne separe pas les deux Combattants (memes valeurs),
  la carte est defaussee et personne ne marque.
- **Plafond de 7 cartes** : sans plafond, deux Combattants aux caracteristiques identiques
  ne se separeraient jamais. Au-dela de 7 cartes revelees, le joueur ayant remporte le
  plus de batailles remporte le duel ; a egalite, double victoire (les deux infligent
  leurs Degats, conformement a `game.md`). En pratique, ~7 % des duels sont tranches par
  ce plafond.
- **Dos d'une carte multi-caracteristiques** : une couleur unique, choisie parmi celles que
  la condition lit et **figee** par carte (fidele a un jeu physique imprime).
- **2 pioches persistantes** : les 20 cartes sont melangees puis coupees en 2 pioches de 10
  qui restent en place toute la partie. Les cartes d'un duel rejoignent la defausse a la
  fin de ce duel ; si une pioche s'epuise, la defausse est melangee et repartie sous les
  deux pioches.
- **Ordre des batailles** : en commencant par J1, puis strictement a tour de role — celui
  qui remporte une bataille ne rejoue pas.
- **Choix des Combattants** : J1 engage face visible, J2 choisit ensuite en le connaissant
  (comme `game.md`). J1 est compense par le fait de piocher la premiere carte Bataille.
- **Degats fixes** : le vainqueur inflige exactement ses Degats, que le duel finisse 3-0 ou
  3-2.
- **Equipe visible** : le roster complet des deux joueurs est visible en permanence ; seuls
  le contenu des pioches (hors couleur du dos) reste cache.
- **Moteur de Pouvoirs retire** : `engine/powers.py` n'existe plus dans cette version (le
  champ `pouvoir` des Combattants reste en donnees). `pouvoirs.csv` est conserve pour une
  version ulterieure.

## Verifier l'equilibre

```
uv run python generate_metagame.py -n 3000
```

Simule des parties completes IA contre IA (la meme heuristique des deux cotes, equipes
tirees au hasard) et affiche le pourcentage de victoire par Combattant. Sur le roster
fourni, les 22 Combattants tiennent dans une fourchette de 6 points (43,6 % a 49,9 %, le
solde etant les parties nulles).

## Tests effectues

- 2 000 parties completes simulees via le moteur Python (sans crash), avec mesure du
  rythme : duels de 3 a 7 cartes (4,8 en moyenne), 16,8 % de batailles nulles, 6,6 % de
  duels tranches par le plafond, 32,5 % de parties finies par KO.
- Equilibrage mesure sur les 231 paires de Combattants possibles (400 duels par paire) :
  ecart maximal entre PV infliges et PV subis de 0,31 PV par duel.
- Partie complete jouee via l'API HTTP reelle (serveur Flask demarre), verifiant le cycle
  choix du Combattant → batailles alternees → fin de duel (par 3 batailles et par
  plafond) → duel suivant → KO, ainsi que le reapprovisionnement des pioches depuis la
  defausse.
- Verification visuelle du frontend (ecran de selection et ecran de duel) par captures en
  navigateur headless.
