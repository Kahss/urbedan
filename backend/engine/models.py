"""Modeles de donnees d'Urban Eredan (version Eredice) : Des de pouvoir, Personnages,
Joueurs.

Cette version remplace les Glyphes / duels 1v1 par un draft de Des de pouvoir en 3v3
(cf. versions/eredice.md).
"""
import itertools
import json
import random

# ------------------------------------------------------------------ Des de pouvoir

COULEURS = ("rouge", "bleu", "jaune")

# Les 7 Des de pouvoir sont identiques : 6 faces, 2 par couleur (rouge, rouge, bleu,
# bleu, jaune, jaune). Un lancer est donc uniforme sur les 3 couleurs, mais les faces
# sont modelisees telles quelles pour rester fidele au materiel physique.
FACES_DE = ("rouge", "rouge", "bleu", "bleu", "jaune", "jaune")

NB_DES_POOL = 7

_de_id_counter = itertools.count(1)


class De:
    """Un De de pouvoir, avec la couleur resultant de son lancer."""

    def __init__(self, couleur=None):
        self.id = next(_de_id_counter)
        self.couleur = couleur if couleur is not None else random.choice(FACES_DE)

    def relancer(self):
        self.couleur = random.choice(FACES_DE)

    def to_dict(self):
        return {"id": self.id, "couleur": self.couleur}


def lancer_pool(nombre=NB_DES_POOL):
    """Tire les Des de pouvoir du round."""
    return [De() for _ in range(nombre)]


# ------------------------------------------------------------------- Personnages


class PersonnageTemplate:
    """Definition statique d'un Personnage, chargee depuis data/personnages.json."""

    def __init__(self, data):
        self.id = data["id"]
        self.nom = data["nom"]
        self.initiative = data["initiative"]
        self.attaque = data["attaque"]
        self.capacites = data.get("capacites", [])

    def to_dict(self):
        return {
            "id": self.id,
            "nom": self.nom,
            "initiative": self.initiative,
            "attaque": self.attaque,
            "capacites": self.capacites,
        }


class PersonnageEnJeu:
    """Instance d'un Personnage dans une partie : suit ses Des stockes, son bonus
    d'Attaque acquis en cours de partie et s'il a deja attaque ce round."""

    def __init__(self, template, joueur):
        self.template = template
        self.joueur = joueur
        self.des_stockes = []        # liste de De (ressources accumulees)
        self.bonus_attaque = 0      # modifications permanentes d'Attaque
        self.a_attaque = False      # une seule attaque par round et par personnage
        self.activations = 0        # nombre total de capacites activees dans la partie

    @property
    def attaque(self):
        """Valeur d'Attaque courante, jamais negative."""
        return max(0, self.template.attaque + self.bonus_attaque)

    def couleurs_stockees(self):
        return [d.couleur for d in self.des_stockes]

    def to_dict(self, position_piste=None):
        return {
            "id": self.template.id,
            "nom": self.template.nom,
            "initiative": self.template.initiative,
            "attaque_base": self.template.attaque,
            "attaque": self.attaque,
            "bonus_attaque": self.bonus_attaque,
            "capacites": self.template.capacites,
            "des_stockes": [d.to_dict() for d in self.des_stockes],
            "a_attaque": self.a_attaque,
            "proprietaire": self.joueur.nom,
            "position_piste": position_piste,
        }


# ----------------------------------------------------------------------- Joueurs

PV_DEPART = 20


class Joueur:
    def __init__(self, nom, est_ia):
        self.nom = nom
        self.est_ia = est_ia
        self.pv = PV_DEPART
        self.equipe = []  # liste de PersonnageEnJeu (3)

    def personnage(self, personnage_id):
        return next((p for p in self.equipe if p.template.id == personnage_id), None)

    def to_dict(self):
        return {
            "nom": self.nom,
            "est_ia": self.est_ia,
            "pv": self.pv,
            "equipe": [p.to_dict() for p in self.equipe],
        }


def charger_personnages(chemin_json):
    with open(chemin_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {p["id"]: PersonnageTemplate(p) for p in data["personnages"]}
