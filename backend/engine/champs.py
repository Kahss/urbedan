"""Cartes Champ de bataille : le terrain commun sur lequel se resout chaque duel.

Une carte comporte 3 cases, une par Zone (Bitume / Hauteur / Souterrain). Chaque case
porte une valeur de -2 a 6. Un Combattant ne beneficie que des cases listees dans sa
caracteristique `avantage` : il ajoute leurs valeurs a sa Puissance.

Le dos de la carte ne devoile **qu'une seule case**, designee par le modele : sa couleur y
apparait, verte si sa valeur est positive, rouge si elle est negative. Les deux autres
cases restent grises, ce qui signifie "inconnu". La case devoilee n'est jamais nulle,
faute de quoi elle s'afficherait grise elle aussi et serait indistinguable d'une case
inconnue.

Chaque modele est decline en 3 rotations (les memes cases, decalees d'une Zone, la case
devoilee suivant le meme decalage). Sur l'ensemble du deck, les 3 Zones voient donc
exactement le meme multi-ensemble de cases et sont devoilees exactement aussi souvent :
aucune Zone n'est structurellement meilleure qu'une autre, et deux Combattants dont
l'`avantage` a la meme taille partent strictement a egalite.
"""
import itertools
import random

# Les 3 Zones d'un champ de bataille, dans l'ordre des cases (index 1, 2, 3 dans la
# caracteristique `avantage` d'un Combattant).
ZONES = ["Bitume", "Hauteur", "Souterrain"]

# Modeles de champ de bataille : la valeur de chacune des 3 cases, et l'index (0 a 2) de
# la case devoilee au dos. La majorite des modeles presentent 2 cases vertes et 1 case
# grise ou rouge ; "Nuit blanche" (tout vert) et "Terrain condamne" (tout gris/rouge) sont
# les deux variantes extremes. 6 modeles devoilent une case verte, 4 une case rouge : le
# dos est donc autant une promesse qu'un avertissement.
MODELES = [
    {"nom": "Nuit calme", "cases": [3, 2, 0], "revele": 0},
    {"nom": "Quartier ouvert", "cases": [4, 1, 0], "revele": 1},
    {"nom": "Halo urbain", "cases": [2, 1, 0], "revele": 0},
    {"nom": "Terrain conteste", "cases": [4, 2, -1], "revele": 2},
    {"nom": "Zone de chantier", "cases": [5, 1, -2], "revele": 0},
    {"nom": "Couvre-feu", "cases": [2, 1, -2], "revele": 2},
    {"nom": "Ligne de faille", "cases": [6, 1, -2], "revele": 2},
    {"nom": "Nuit blanche", "cases": [3, 2, 1], "revele": 2},
    {"nom": "Rue barree", "cases": [4, 0, -1], "revele": 0},
    {"nom": "Terrain condamne", "cases": [0, -1, -2], "revele": 1},
]

NB_ROTATIONS = 3
INCONNU = "inconnu"

_compteur_champ = itertools.count(1)


def couleur(valeur):
    """Couleur d'une case dont la valeur est connue (recto)."""
    if valeur > 0:
        return "vert"
    if valeur == 0:
        return "gris"
    return "rouge"


def _rotations(cases, revele):
    """Les 3 declinaisons d'un modele : cases et case devoilee decalees ensemble."""
    return [
        (tuple(cases[-r:] + cases[:-r]) if r else tuple(cases), (revele + r) % NB_ROTATIONS)
        for r in range(NB_ROTATIONS)
    ]


def _valider_modeles():
    """La case devoilee doit toujours etre franchement positive ou franchement negative :
    une case devoilee nulle serait grise, donc confondue avec une case inconnue."""
    for modele in MODELES:
        if len(modele["cases"]) != NB_ROTATIONS:
            raise ValueError(f"{modele['nom']} : 3 cases attendues")
        if modele["cases"][modele["revele"]] == 0:
            raise ValueError(f"{modele['nom']} : la case devoilee ne peut pas etre nulle")


_valider_modeles()


class ChampDeBataille:
    def __init__(self, nom, cases, revele):
        self.id = next(_compteur_champ)
        self.nom = nom
        self.cases = tuple(cases)
        self.revele = revele  # index de la case devoilee au dos

    def dos(self):
        """Les 3 couleurs visibles au dos : celle de la case devoilee, et "inconnu" pour
        les deux autres. Seule information disponible avant la revelation."""
        return [
            couleur(valeur) if i == self.revele else INCONNU
            for i, valeur in enumerate(self.cases)
        ]

    def bonus(self, avantage):
        """Somme des valeurs des cases couvertes par l'`avantage` du Combattant."""
        return sum(self.cases[index - 1] for index in avantage)

    def detail(self, avantage):
        """(zone, valeur) pour chaque case couverte, pour tracer le calcul de Puissance."""
        return [(ZONES[index - 1], self.cases[index - 1]) for index in avantage]

    def to_dict(self, revele):
        """Le dos est toujours transmis ; le recto (nom du modele, valeurs) n'est transmis
        qu'une fois la carte revelee, jamais pendant la phase de choix."""
        data = {"id": self.id, "dos": self.dos(), "revele": revele}
        if revele:
            data["nom"] = self.nom
            data["case_devoilee"] = self.revele
            data["cases"] = [
                {"zone": ZONES[i], "valeur": valeur, "couleur": couleur(valeur)}
                for i, valeur in enumerate(self.cases)
            ]
        return data


def construire_deck():
    """Le deck complet, melange : 10 modeles x 3 rotations = 30 cartes."""
    deck = [
        ChampDeBataille(modele["nom"], cases, revele)
        for modele in MODELES
        for cases, revele in _rotations(modele["cases"], modele["revele"])
    ]
    random.shuffle(deck)
    return deck


def faces_du_deck():
    """Les 30 faces possibles (sans identite de carte), pour l'estimation de l'IA."""
    return [
        (modele["nom"], cases, revele)
        for modele in MODELES
        for cases, revele in _rotations(modele["cases"], modele["revele"])
    ]


def catalogue():
    """Composition du deck, pour la legende du frontend. Les valeurs sont donnees dans
    l'orientation de reference : chaque modele est aussi present avec ses cases decalees
    d'une Zone et de deux Zones."""
    return [
        {
            "nom": modele["nom"],
            "revele": modele["revele"],
            "cases": [
                {"valeur": valeur, "couleur": couleur(valeur), "devoilee": i == modele["revele"]}
                for i, valeur in enumerate(modele["cases"])
            ],
            "exemplaires": NB_ROTATIONS,
        }
        for modele in MODELES
    ]
