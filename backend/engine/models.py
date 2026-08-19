"""Modeles de donnees pour Urban Eredan, version duo : Combattants, Joueurs.

Version duo (voir versions/duo.md) : les Glyphes ont disparu, donc l'Energie aussi.
Un Combattant n'apporte plus que sa Puissance, ses Degats et son unique Pouvoir,
toujours actif. Chaque Combattant ne peut etre engage que MAX_UTILISATIONS fois sur
l'ensemble de la partie.
"""
import itertools

PV_DEPART = 20
TAILLE_EQUIPE = 4
TAILLE_DUO = 2
MAX_UTILISATIONS = 2


class CombattantTemplate:
    """Definition statique d'un Combattant, chargee depuis data/combattants.json."""

    def __init__(self, data):
        self.id = data["id"]
        self.nom = data["nom"]
        self.puissance = data["puissance"]
        self.degats = data["degats"]
        self.pouvoir = data["pouvoir"]  # dict unique (description, condition, modificateur, effets)

    def to_dict(self):
        return {
            "id": self.id,
            "nom": self.nom,
            "puissance": self.puissance,
            "degats": self.degats,
            "pouvoir": self.pouvoir,
        }


class CombattantEnEquipe:
    """Une instance de Combattant au sein d'une equipe, qui suit combien de fois elle a
    deja ete engagee (MAX_UTILISATIONS au total sur la partie)."""

    def __init__(self, template):
        self.template = template
        self.utilisations = 0

    def disponible(self):
        return self.utilisations < MAX_UTILISATIONS

    def utilisations_restantes(self):
        return max(0, MAX_UTILISATIONS - self.utilisations)

    def to_dict(self):
        return {
            "id": self.template.id,
            "nom": self.template.nom,
            "puissance": self.template.puissance,
            "degats": self.template.degats,
            "pouvoir": self.template.pouvoir,
            "utilisations": self.utilisations,
            "utilisations_max": MAX_UTILISATIONS,
            "utilisations_restantes": self.utilisations_restantes(),
            "disponible": self.disponible(),
        }


def calendrier_faisable(utilisations_restantes, batailles_restantes):
    """Un joueur peut-il encore engager un duo de 2 Combattants distincts a chacune des
    `batailles_restantes` batailles a venir ?

    Chaque bataille consomme 2 slots, et un meme Combattant ne peut occuper qu'un seul
    slot par bataille : le nombre de slots qu'un Combattant peut remplir sur k batailles
    vaut donc min(utilisations restantes, k). Le calendrier tient si la somme de ces
    contributions couvre les 2*k slots a pourvoir.

    C'est ce qui rend illegaux les duos qui concentrent les utilisations restantes sur
    trop peu de Combattants : avec 4 Combattants a 2 utilisations pour 4 batailles, jouer
    {A,B} puis {A,C} puis {B,C} laisserait D seul avec 2 utilisations pour la derniere
    bataille, qui exige 2 Combattants distincts.
    """
    k = batailles_restantes
    if k <= 0:
        return True
    return sum(min(restantes, k) for restantes in utilisations_restantes) >= TAILLE_DUO * k


class Joueur:
    def __init__(self, nom, est_ia, equipe):
        self.nom = nom
        self.est_ia = est_ia
        self.pv = PV_DEPART
        self.equipe = equipe  # liste de CombattantEnEquipe (TAILLE_EQUIPE)

    def combattants_disponibles(self):
        return [c for c in self.equipe if c.disponible()]

    def duos_legaux(self, batailles_restantes):
        """Duos (paires de Combattants distincts disponibles) jouables a cette bataille
        sans rendre le calendrier des batailles suivantes infaisable.

        Si aucun duo ne preserve la faisabilite (cas theoriquement impossible tant que
        cette methode est la seule porte d'entree des choix, mais qui ne doit jamais
        bloquer la partie), toutes les paires disponibles sont rendues.
        """
        disponibles = self.combattants_disponibles()
        paires = list(itertools.combinations(disponibles, TAILLE_DUO))
        apres = batailles_restantes - 1
        legaux = []
        for paire in paires:
            restantes = [
                c.utilisations_restantes() - (1 if c in paire else 0) for c in self.equipe
            ]
            if calendrier_faisable(restantes, apres):
                legaux.append(paire)
        return legaux or paires

    def to_dict(self):
        return {
            "nom": self.nom,
            "est_ia": self.est_ia,
            "pv": self.pv,
            "pv_max": PV_DEPART,
            "equipe": [c.to_dict() for c in self.equipe],
        }
