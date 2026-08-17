"""Modeles de donnees pour Urban Eredan : Combattants, Joueurs."""

NB_ZONES = 3


class DonneesInvalides(Exception):
    pass


def valider_avantage(avantage, nom):
    """L'`avantage` est la liste des Zones du champ de bataille dont le Combattant tire
    parti : entre 1 et 3 index distincts compris entre 1 et 3."""
    if not isinstance(avantage, list) or not 1 <= len(avantage) <= NB_ZONES:
        raise DonneesInvalides(f"{nom} : 'avantage' doit contenir entre 1 et {NB_ZONES} Zones")
    if len(set(avantage)) != len(avantage):
        raise DonneesInvalides(f"{nom} : 'avantage' ne peut pas repeter une Zone")
    for index in avantage:
        if not isinstance(index, int) or not 1 <= index <= NB_ZONES:
            raise DonneesInvalides(f"{nom} : Zone invalide dans 'avantage' ({index})")
    return sorted(avantage)


class CombattantTemplate:
    """Definition statique d'un Combattant, chargee depuis data/combattants.json."""

    def __init__(self, data):
        self.id = data["id"]
        self.nom = data["nom"]
        self.puissance = data["puissance"]
        self.degats = data["degats"]
        self.avantage = valider_avantage(data["avantage"], data["nom"])
        self.pouvoir = data["pouvoir"]  # dict unique (description, condition, modificateur, effets)

    def to_dict(self):
        return {
            "id": self.id,
            "nom": self.nom,
            "puissance": self.puissance,
            "degats": self.degats,
            "avantage": self.avantage,
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
