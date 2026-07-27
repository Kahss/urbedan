# Contexte
Tu dois générer un prototype de jeu vidéo permettant de jouer au jeu de société Urban Eredan

# Fichiers
Les règles du jeu se trouvent dans `game.md`.
La liste des mots clés, leur type et leur descriptif nécessaire pour la création des Pouvoirs des Combattants se trouve dans `pouvoirs.csv`.

# Frontend
- Doit être une page web (HTML, CSS, JS)
- Pas de framework particulier à utiliser. Utilise ceux qui présentent le meilleur rapport qualité / facilité de génération pour générer un POC
- Le jeu doit être jouable uniquement avec des clics
- Il n'y a pas d'illustrations à utiliser pour les Combattants ou les Glyphes. Le design des cartes doit être clair et lisible en utilisant uniquement du texte.

# Backend
- Doit être développé en Python
- Doit permettre de jouer au jeu comme décrit dans `game.md`.

# Combattants
- La liste des combattants jouable doit être stockée sous la forme d'un fichier json que je pourrai éditer manuellement.
- Génère un ensemble de 8 personnages cohérents avec les règles pour pouvoir tester le POC

# IA
Le jeu doit être jouable en solo, avec une IA adverse qui choisit un Combattant et un Glyphe aléatoire de sa main lorsque c'est son tour.