"""Cartes Champ de bataille : le terrain commun sur lequel se resout chaque duel.

Une carte comporte 3 cases, une par Zone (Bitume / Hauteur / Souterrain). Chaque case
porte une valeur (de -2 a 6) et eventuellement un point d'Energie. Un Combattant ne
beneficie que des cases listees dans sa caracteristique `avantage` : il ajoute leurs
valeurs a sa Puissance et cumule leur Energie.

Le dos de la carte ne montre que la couleur de chaque case : vert si la valeur est
positive, gris si elle est nulle, rouge si elle est negative. C'est la seule information
disponible au moment ou les joueurs engagent leur Combattant : ni les valeurs exactes,
ni la presence d'Energie ne sont connues avant la revelation.

Chaque modele de carte est decline en 3 rotations (les memes cases, decalees d'une Zone).
Sur l'ensemble du deck, les 3 Zones voient donc exactement le meme multi-ensemble de
cases : aucune Zone n'est structurellement meilleure qu'une autre, et deux Combattants
dont l'`avantage` a la meme taille partent strictement a egalite.
"""
import itertools
import random

# Les 3 Zones d'un champ de bataille, dans l'ordre des cases (index 1, 2, 3 dans la
# caracteristique `avantage` d'un Combattant).
ZONES = ["Bitume", "Hauteur", "Souterrain"]

# Modeles de champ de bataille : (valeur, energie) pour chacune des 3 cases.
# La majorite des modeles (7 sur 10) presentent 2 cases vertes et 1 case grise ou rouge,
# conformement au profil moyen attendu ; "Nuit blanche" (tout vert) et "Terrain condamne"
# (tout gris/rouge) sont les deux variantes extremes.
# L'Energie est volontairement plus frequente sur les cases grises et rouges que sur les
# vertes : subir une mauvaise case reste un lot de consolation qui allume un Pouvoir.
MODELES = [
    {"nom": "Nuit calme", "cases": [(3, 0), (2, 1), (0, 1)]},
    {"nom": "Quartier ouvert", "cases": [(4, 0), (1, 1), (0, 1)]},
    {"nom": "Halo urbain", "cases": [(2, 1), (1, 1), (0, 1)]},
    {"nom": "Terrain conteste", "cases": [(4, 0), (2, 0), (-1, 1)]},
    {"nom": "Zone de chantier", "cases": [(5, 0), (1, 1), (-2, 1)]},
    {"nom": "Couvre-feu", "cases": [(2, 1), (1, 1), (-2, 0)]},
    {"nom": "Ligne de faille", "cases": [(6, 0), (1, 0), (-2, 1)]},
    {"nom": "Nuit blanche", "cases": [(3, 0), (2, 0), (1, 1)]},
    {"nom": "Rue barree", "cases": [(4, 0), (0, 1), (-1, 1)]},
    {"nom": "Terrain condamne", "cases": [(0, 1), (-1, 1), (-2, 1)]},
]

NB_ROTATIONS = 3

_compteur_champ = itertools.count(1)


def couleur(valeur):
    if valeur > 0:
        return "vert"
    if valeur == 0:
        return "gris"
    return "rouge"


def _rotations(cases):
    """Les 3 declinaisons d'un modele : les memes cases, decalees d'une Zone a chaque
    fois. Garantit que chaque Zone recoit exactement le meme multi-ensemble de cases sur
    l'ensemble du deck."""
    return [tuple(cases[-r:] + cases[:-r]) if r else tuple(cases) for r in range(NB_ROTATIONS)]


class ChampDeBataille:
    def __init__(self, nom, cases):
        self.id = next(_compteur_champ)
        self.nom = nom
        self.cases = tuple(cases)  # ((valeur, energie), x3)

    def dos(self):
        """Les 3 couleurs visibles au dos, seule information connue avant la revelation."""
        return [couleur(valeur) for valeur, _ in self.cases]

    def bonus(self, avantage):
        """Somme des valeurs des cases couvertes par l'`avantage` du Combattant."""
        return sum(self.cases[index - 1][0] for index in avantage)

    def energie(self, avantage):
        """Somme des points d'Energie des cases couvertes par l'`avantage`."""
        return sum(self.cases[index - 1][1] for index in avantage)

    def detail(self, avantage):
        """(zone, valeur) pour chaque case couverte, pour tracer le calcul de Puissance."""
        return [(ZONES[index - 1], self.cases[index - 1][0]) for index in avantage]

    def to_dict(self, revele):
        """Le dos est toujours transmis ; le recto (nom du modele, valeurs, Energie) n'est
        transmis qu'une fois la carte revelee, jamais pendant la phase de choix."""
        data = {"id": self.id, "dos": self.dos(), "revele": revele}
        if revele:
            data["nom"] = self.nom
            data["cases"] = [
                {"zone": ZONES[i], "valeur": valeur, "energie": energie, "couleur": couleur(valeur)}
                for i, (valeur, energie) in enumerate(self.cases)
            ]
        return data


def construire_deck():
    """Le deck complet, melange : 10 modeles x 3 rotations = 30 cartes."""
    deck = [
        ChampDeBataille(modele["nom"], cases)
        for modele in MODELES
        for cases in _rotations(modele["cases"])
    ]
    random.shuffle(deck)
    return deck


def faces_du_deck():
    """Les 30 faces possibles (sans identite de carte), pour l'estimation de l'IA."""
    return [
        (modele["nom"], cases)
        for modele in MODELES
        for cases in _rotations(modele["cases"])
    ]


def catalogue():
    """Composition du deck, pour la legende du frontend. Les valeurs sont donnees dans
    l'orientation de reference : chaque modele est aussi present avec ses cases decalees
    d'une Zone et de deux Zones."""
    return [
        {
            "nom": modele["nom"],
            "cases": [
                {"valeur": valeur, "energie": energie, "couleur": couleur(valeur)}
                for valeur, energie in modele["cases"]
            ],
            "exemplaires": NB_ROTATIONS,
        }
        for modele in MODELES
    ]
