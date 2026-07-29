"""Modeles de donnees pour Urban Eredan : Glyphes, Combattants, Joueurs."""
import itertools
import random

# Repartition des Glyphes definie dans game.md : (puissance, energie, quantite)
GLYPH_DISTRIBUTION = [
    (6, 0, 2),
    (4, 1, 4),
    (2, 2, 4),
    (0, 3, 2),
]

_glyphe_id_counter = itertools.count(1)


class Glyphe:
    def __init__(self, puissance, energie):
        self.id = next(_glyphe_id_counter)
        self.puissance = puissance
        self.energie = energie

    def notation_txt(self):
        return f"{self.puissance}/{self.energie}"

    def to_dict(self):
        return {
            "id": self.id,
            "puissance": self.puissance,
            "energie": self.energie,
            "notation": self.notation_txt(),
        }


def construire_deck_glyphes():
    deck = []
    for puissance, energie, quantite in GLYPH_DISTRIBUTION:
        for _ in range(quantite):
            deck.append(Glyphe(puissance, energie))
    random.shuffle(deck)
    return deck


class CombattantTemplate:
    """Definition statique d'un Combattant, chargee depuis data/combattants.json."""

    def __init__(self, data):
        self.id = data["id"]
        self.nom = data["nom"]
        self.puissance = data["puissance"]
        self.degats = data["degats"]
        self.pouvoir = data["pouvoir"]  # dict unique (description, condition, modificateur, energie_min, effets)

    def to_dict(self):
        return {
            "id": self.id,
            "nom": self.nom,
            "puissance": self.puissance,
            "degats": self.degats,
            "pouvoir": self.pouvoir,
        }


class CombattantEnEquipe:
    """Une instance de Combattant au sein d'une equipe (suit s'il a deja combattu)."""

    def __init__(self, template):
        self.template = template
        self.utilise = False

    def to_dict(self):
        return {
            "id": self.template.id,
            "nom": self.template.nom,
            "puissance": self.template.puissance,
            "degats": self.template.degats,
            "pouvoir": self.template.pouvoir,
            "utilise": self.utilise,
        }


class Joueur:
    def __init__(self, nom, est_ia, equipe):
        self.nom = nom
        self.est_ia = est_ia
        self.pv = 12
        self.equipe = equipe  # liste de CombattantEnEquipe (4)
        self.glyphe_courant = None  # Glyphe pioche pour le duel en cours

    def combattants_disponibles(self):
        return [c for c in self.equipe if not c.utilise]

    def to_dict(self, cacher_glyphe=False):
        return {
            "nom": self.nom,
            "est_ia": self.est_ia,
            "pv": self.pv,
            "equipe": [c.to_dict() for c in self.equipe],
            "glyphe_courant": (
                None if (cacher_glyphe or self.glyphe_courant is None) else self.glyphe_courant.to_dict()
            ),
            "a_glyphe_courant": self.glyphe_courant is not None,
        }
