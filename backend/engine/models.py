"""Modeles de donnees pour Urban Eredan : Cartes Puissance, Combattants, Joueurs."""
import itertools
import random

# Repartition des Cartes Puissance definie dans versions/stop_ou_encore.md :
# (nom, puissance, malus, quantite). Tas de 20 cartes, remelange a chaque duel.
# `malus` (Y) n'est plus un seuil de "bust" : les joueurs piochent librement autant de
# cartes qu'ils veulent. A la resolution du duel, la somme des `malus` des cartes
# piochees par un Combattant est retranchee en Vie (PV) a son ADVERSAIRE si celui-ci
# remporte le duel (version testee, cf. powers.py) : le Malus ne coute donc rien a
# celui qui l'a pioche lui-meme.
# Deck "Audacieux" : solde moyen (Puissance - Malus) delibrement positif (+0.30/carte,
# contre 0 pour le deck d'origine), pour pousser a piocher plus longtemps. Les noms de
# carte sont conserves a l'identique (Destin/Épreuve/Péripétie/Adversité), seules les
# quantites changent, car plusieurs Pouvoirs de Combattant ciblent ces noms precis
# (transforme_carte_type/annule_type_carte/annule_premiere_carte_type/revele_type_carte
# - cf. Shifu, Neo, Morpheus, Po, Oogway dans data/combattants.json).
CARTE_PUISSANCE_DISTRIBUTION = [
    ("Destin", 2, 0, 4),
    ("Épreuve", 1, 1, 9),
    ("Péripétie", 0, 0, 6),
    ("Adversité", 0, 2, 1),
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
        self.malus_limite = data.get("malus_limite", 3)  # seuil de Malus total pour la condition "surcharge"
        self.image = data.get("image")

    def to_dict(self):
        return {
            "id": self.id,
            "nom": self.nom,
            "puissance": self.puissance,
            "degats": self.degats,
            "niveau": self.niveau,
            "pouvoir": self.pouvoir,
            "malus_limite": self.malus_limite,
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
            "malus_limite": self.template.malus_limite,
            "image": self.template.image,
            "utilise": self.utilise,
        }


class Joueur:
    def __init__(self, nom, est_ia, equipe):
        self.nom = nom
        self.est_ia = est_ia
        self.pv = 20  # ecrase par Partie.PV_DEPART a la mise en place (cf. game.py)
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
