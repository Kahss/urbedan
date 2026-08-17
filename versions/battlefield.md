# Version avec résolution par carte "champ de bataille"

- Dans cette version, la résolution du combat se fait par la révélation d'une carte "champ de bataille" une fois que les deux personnages ont été choisis
- Les personnages gardent leurs caractéristiques actuelles, avec en plus une nouvelle caractéristique "avantage"
- l'avantage est une liste de nombre qui contient entre 1 et 3 chiffres compris entre 1 et 3 (par exemple [1, 2])
- Cette caractéristique est utilisée via le champ de bataille pour déterminer qui remporte le duel
- Une carte champ de bataille est une carte qui comprend 3 cases, chacune comprenant une valeur entre -2 et 6. Chaque case peut aussi contenir un éventuel point d'énergie
- Le dos de la carte champ de bataille comprend aussi 3 cases, mais cette fois avec des couleurs. Les couleurs sont déterminées par les valeurs au recto de la carte : si la valeur est positive, elle est verte, si elle est nulle, elle est grise, et si elle est négative, elle est rouge. Ainsi, une carte champ de bataille [2 et 1 énergie, 3, -2] aurait un verso égal à [vert, vert, rouge].
- Ce dos de carte est là pour donner une première informations aux joueurs sur le contenu du champ de bataille, sans pour autant donner la valeur exacte des cases.
- En moyenne, les champs de batailles contiennent 2 cases vertes et une case grise/rouge, avec des variantes pour des champs de batailles plus extrêmes (tout vert ou tout rouge par exemple)
- Le déroulé du tour se passe donc comme suit :
  - Révélation du dos de la carte champ de bataille du round
  - J1 choisit son perso
  - J2 choisit son perso
  - Révélation du champ de bataille et calcul des puissances respectives