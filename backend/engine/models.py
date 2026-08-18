"""Modeles de donnees pour Urban Eredan : Combattants, Joueurs.

Dans cette version, un Combattant n'a plus de Puissance ni de Pouvoir : il porte trois
caracteristiques (Force, Dexterite, Sagesse), chacune de 0 a 5, avec lesquelles il
dispute les batailles du duel. Les cartes Glyphes et l'Energie ont disparu ; le champ
`pouvoir` de data/combattants.json est conserve pour une version ulterieure mais n'est
lu ni par le moteur ni par le frontend.
"""
from .batailles import CARACS


class CombattantTemplate:
    """Definition statique d'un Combattant, chargee depuis data/combattants.json."""

    def __init__(self, data):
        self.id = data["id"]
        self.nom = data["nom"]
        self.force = data["force"]
        self.dexterite = data["dexterite"]
        self.sagesse = data["sagesse"]
        self.degats = data["degats"]
        for carac in CARACS:
            valeur = getattr(self, carac)
            if not 0 <= valeur <= 5:
                raise ValueError(f"{self.nom} : {carac} = {valeur}, attendu entre 0 et 5")

    @property
    def caracs(self):
        return {carac: getattr(self, carac) for carac in CARACS}

    def to_dict(self):
        return {
            "id": self.id,
            "nom": self.nom,
            "force": self.force,
            "dexterite": self.dexterite,
            "sagesse": self.sagesse,
            "total_caracs": sum(self.caracs.values()),
            "degats": self.degats,
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
