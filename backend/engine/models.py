"""Modeles de donnees pour Urban Eredan : Combattants, Joueurs.

Version "draft de des" : il n'y a plus de cartes Glyphes ni de puissance de base. La
Puissance et l'Energie d'un Combattant proviennent des 3 des qu'il drafte dans le pool
central du duel. La seule caracteristique chiffree qui remplace la Puissance est
l'`initiative`, qui determine qui drafte en premier.
"""


class CombattantTemplate:
    """Definition statique d'un Combattant, chargee depuis data/combattants.json."""

    def __init__(self, data):
        self.id = data["id"]
        self.nom = data["nom"]
        self.initiative = data["initiative"]
        self.degats = data["degats"]
        self.pouvoir = data["pouvoir"]  # dict unique (description, condition, modificateur, energie_min, effets)

    def to_dict(self):
        return {
            "id": self.id,
            "nom": self.nom,
            "initiative": self.initiative,
            "degats": self.degats,
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
