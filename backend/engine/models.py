"""Modeles de donnees pour Urban Eredan : Combattants, Joueurs.

Version "des par personnage" : il n'y a plus de cartes Glyphes ni de puissance de base.
Chaque Combattant porte deux listes de des :
- `des_personnels` : les des qu'il lance lui-meme pour determiner sa Puissance/Energie ;
- `des_adverses`  : les des qu'il donne a l'adversaire du duel, qui les ajoute a ses
  propres des personnels.
"""
from .des import valider_de, de_to_dict


class CombattantTemplate:
    """Definition statique d'un Combattant, chargee depuis data/combattants.json."""

    def __init__(self, data):
        self.id = data["id"]
        self.nom = data["nom"]
        self.degats = data["degats"]
        self.des_personnels = [valider_de(d) for d in data.get("des_personnels", [])]
        self.des_adverses = [valider_de(d) for d in data.get("des_adverses", [])]
        self.pouvoir = data["pouvoir"]  # dict unique (description, condition, modificateur, energie_min, effets)

    def to_dict(self):
        return {
            "id": self.id,
            "nom": self.nom,
            "degats": self.degats,
            "des_personnels": [de_to_dict(d) for d in self.des_personnels],
            "des_adverses": [de_to_dict(d) for d in self.des_adverses],
            "pouvoir": self.pouvoir,
        }


class CombattantEnEquipe:
    """Une instance de Combattant au sein d'une equipe (suit s'il a deja combattu)."""

    def __init__(self, template):
        self.template = template
        self.utilise = False

    def to_dict(self):
        data = self.template.to_dict()
        data["utilise"] = self.utilise
        return data


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
