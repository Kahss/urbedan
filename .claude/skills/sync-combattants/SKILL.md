---
name: sync-combattants
description: Répercute une mise à jour de "data/Urban Eredan - Cartes - Combattants.csv" (le tableur source des personnages) vers data/combattants.json et, si besoin, le moteur (backend/engine/*.py). Trigger -- l'utilisateur dit que le CSV des Combattants a été mis à jour, demande de synchroniser/répercuter les personnages, ou invoque /sync-combattants.
---

# Sync des Combattants (CSV -> JSON -> moteur)

Le fichier `data/Urban Eredan - Cartes - Combattants.csv` (export du tableur) est la
source de vérité éditée à la main par l'utilisateur. `data/combattants.json` est la
donnée réellement consommée par le jeu (`backend/engine/models.py` charge ce JSON).
Après une édition du CSV, ces deux fichiers divergent : ce skill les reconcilie.

## Méthode

1. **Isoler le changement.** Si le CSV est suivi par git, préférer
   `git diff -- "data/Urban Eredan - Cartes - Combattants.csv"` pour ne regarder que
   les lignes réellement modifiées plutôt que de tout relire à l'aveugle. Sinon, lire
   le CSV en entier (colonnes : `#, Nom, Niveau, Puissance, Dégâts, Capacité`).

2. **Comparer champ par champ avec `data/combattants.json`**, personnage par
   personnage (matching par nom, en tenant compte des accents/majuscules) :
   - `niveau`, `puissance`, `degats` : ce sont des entiers directement comparables au
     JSON. Toute différence numérique doit être répercutée dans le JSON.
   - `Capacité` (texte libre) : ne PAS écraser bêtement `pouvoir.description` avec le
     texte brut du CSV. Le JSON encode le pouvoir via `condition`, `modificateur` et
     `effets` (voir schéma dans `$schema_doc` du JSON et `backend/engine/powers.py`
     pour la liste des `condition`/`modificateur`/`type d'effet` déjà supportés) ; la
     description JSON est volontairement raccourcie (ex: "Domination : +3 Puissance /
     +3 Dégâts" au lieu de "Si vous avez plus de PV que votre adversaire : ...").
     Ne mettre à jour un pouvoir que si le texte du CSV révèle un changement de
     *mécanique réelle* : la valeur numérique de l'effet, sa cible (soi/adversaire), ou
     la condition sous-jacente. Un simple reformulation/renommage (ex: "glyphe" ->
     "carte Puissance", "Glyphes" -> "cartes puissance", "Prophéties" -> "Destin") ne
     nécessite qu'une mise à jour cosmétique de `description` si elle cite ce terme,
     pas une modification des `effets`.
   - Si le nouveau texte de `Capacité` implique une `condition` ou un `type` d'effet
     qui n'existe pas encore dans `backend/engine/powers.py` (`_verifier_condition`,
     `_valeur_effective`, `_resoudre_effet`), NE PAS inventer un mapping approximatif :
     signaler clairement à l'utilisateur quel personnage nécessite du nouveau code
     moteur, et proposer une extension avant de continuer.

3. **Vérifier les cohérences transverses.** `grep` les ids/noms des personnages dont
   les stats ont changé dans `backend/`, `frontend/` et `generate_metagame.py` pour
   détecter un éventuel cas particulier codé en dur qui deviendrait obsolète.

4. **Valider le JSON résultant** (`python3 -c "import json; json.load(open('data/combattants.json'))"`
   ou équivalent) et, si le script existe et que le temps le permet, lancer
   `generate_metagame.py` pour vérifier qu'aucune partie ne plante avec les nouvelles
   valeurs.

5. **Résumer** en fin de tâche les personnages effectivement modifiés (champ, ancienne
   valeur -> nouvelle valeur), et lister explicitement les lignes du CSV qui n'étaient
   que du reformulation sans impact sur le JSON.

## Ce qu'il ne faut pas faire

- Ne pas re-générer `data/combattants.json` depuis zéro à partir du CSV : le JSON
  porte des informations que le CSV n'a pas (`id`, `image`, `condition`,
  `modificateur`, `effets` structurés) et qu'il ne faut pas perdre.
- Ne pas toucher aux personnages dont niveau/puissance/dégâts/mécanique n'ont pas
  changé, même si leur ligne CSV a été retouchée uniquement pour la forme.
- Ne pas modifier `game.md`, `generate_metagame.py` ou d'autres fichiers non liés à
  la donnée des Combattants dans le cadre de ce skill, sauf si l'incohérence détectée
  à l'étape 3 l'exige explicitement.
