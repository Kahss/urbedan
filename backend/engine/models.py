"""Modeles de donnees pour Urban Eredan : Cartes Puissance, Combattants, Joueurs."""
import itertools
import random

# Repartition des Cartes Puissance definie dans versions/stop_ou_encore.md :
# (nom, puissance, malus, quantite). Tas de 20 cartes, remelange a chaque duel.
CARTE_PUISSANCE_DISTRIBUTION = [
    ("Destin", 2, 0, 3),
    ("Épreuve", 1, 1, 7),
    ("Péripétie", 0, 0, 7),
    ("Adversité", 0, 2, 3),
]

_carte_id_counter = itertools.count(1)


class CartePuissance:
    def __init__(self, nom, puissance, malus):
        self.id = next(_carte_id_counter)
        self.nom = nom
        self.puissance = puissance
        self.malus = malus

    def to_dict(self):
        return {
            "id": self.id,
            "nom": self.nom,
            "puissance": self.puissance,
            "malus": self.malus,
        }


def construire_deck_cartes_puissance():
    deck = []
    for nom, puissance, malus, quantite in CARTE_PUISSANCE_DISTRIBUTION:
        for _ in range(quantite):
            deck.append(CartePuissance(nom, puissance, malus))
    random.shuffle(deck)
    return deck


class CombattantTemplate:
    """Definition statique d'un Combattant, chargee depuis data/combattants.json."""

    def __init__(self, data):
        self.id = data["id"]
        self.nom = data["nom"]
        self.puissance = data["puissance"]
        self.degats = data["degats"]
        self.niveau = data["niveau"]  # 1 a 3, 3 = le plus puissant (somme d'equipe plafonnee)
        self.pouvoir = data["pouvoir"]  # dict unique (description, condition, modificateur, energie_min, effets)
        self.image = data.get("image")

    def to_dict(self):
        return {
            "id": self.id,
            "nom": self.nom,
            "puissance": self.puissance,
            "degats": self.degats,
            "niveau": self.niveau,
            "pouvoir": self.pouvoir,
            "image": self.image,
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
            "niveau": self.template.niveau,
            "pouvoir": self.template.pouvoir,
            "image": self.template.image,
            "utilise": self.utilise,
        }


class Joueur:
    def __init__(self, nom, est_ia, equipe):
        self.nom = nom
        self.est_ia = est_ia
        self.pv = 10
        self.equipe = equipe  # liste de CombattantEnEquipe (4)

    def combattants_disponibles(self):
        return [c for c in self.equipe if not c.utilise]

    def to_dict(self):
        return {
            "nom": self.nom,
            "est_ia": self.est_ia,
            "pv": self.pv,
            "equipe": [c.to_dict() for c in self.equipe],
        }
