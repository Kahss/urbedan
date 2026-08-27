"""Cartes Bataille : la resolution d'un duel se fait en remportant 3 batailles.

Un Combattant n'a plus de Puissance mais trois caracteristiques, chacune de 0 a 5 :
Force (rouge), Dexterite (vert), Sagesse (bleu). Une carte Bataille porte au recto une
condition qui designe le vainqueur de la bataille a partir de ces caracteristiques ; si
la condition ne separe pas les deux Combattants, la bataille est nulle et personne ne
marque.

Les cartes sont revelees a l'aveugle : aucune information (couleur ou autre) n'est
disponible avant qu'une carte ne soit effectivement revelee.

Le deck compte 15 cartes distinctes, structurees de facon symetrique : chaque
caracteristique est la caracteristique principale de 4 cartes (3 "la plus haute", 1
somme avec la suivante), auxquelles s'ajoutent 3 cartes globales, grises, qui lisent
les trois caracteristiques. Aucune caracteristique n'est donc structurellement
meilleure qu'une autre.
"""
import itertools
import random

# Les trois caracteristiques, dans l'ordre d'affichage, et leur couleur.
CARACS = ("force", "dexterite", "sagesse")
COULEUR_PAR_CARAC = {"force": "rouge", "dexterite": "vert", "sagesse": "bleu"}
CARAC_PAR_COULEUR = {couleur: carac for carac, couleur in COULEUR_PAR_CARAC.items()}
LIBELLE_CARAC = {"force": "Force", "dexterite": "Dexterite", "sagesse": "Sagesse"}

# Modeles de carte : nom, type de condition et caracteristiques lues, couleur (affichee
# une fois la carte revelee, et utilisee pour le compteur de cartes sorties).
# Les types de condition :
#   max              : la caracteristique la plus haute l'emporte
#   somme            : la somme de deux caracteristiques la plus haute l'emporte
#   total            : le total des trois caracteristiques le plus haut l'emporte
#   meilleure        : la meilleure des trois caracteristiques la plus haute l'emporte
#   pire             : celui dont la plus petite des trois caracteristiques est la plus
#                      faible perd la bataille (donc : la plus petite la plus haute gagne)
# Les caracteristiques tournent en cycle (force -> dexterite -> sagesse -> force) pour
# que les trois groupes de 4 cartes soient rigoureusement equivalents.
MODELES = [
    # --- Force (rouge) : somme avec Dexterite ---
    {"nom": "Bras de fer", "type": "max", "carac": "force", "couleur": "rouge"},
    {"nom": "Mur porteur", "type": "max", "carac": "force", "couleur": "rouge"},
    {"nom": "Rideau de fer", "type": "max", "carac": "force", "couleur": "rouge"},
    {"nom": "Escalade sauvage", "type": "somme", "caracs": ("force", "dexterite"), "couleur": "rouge"},
    # --- Dexterite (vert) : somme avec Sagesse ---
    {"nom": "Toits mouilles", "type": "max", "carac": "dexterite", "couleur": "vert"},
    {"nom": "Slalom de beton", "type": "max", "carac": "dexterite", "couleur": "vert"},
    {"nom": "Cable tendu", "type": "max", "carac": "dexterite", "couleur": "vert"},
    {"nom": "Ligne de fuite", "type": "somme", "caracs": ("dexterite", "sagesse"), "couleur": "vert"},
    # --- Sagesse (bleu) : somme avec Force ---
    {"nom": "Lecture du quartier", "type": "max", "carac": "sagesse", "couleur": "bleu"},
    {"nom": "Signal brouille", "type": "max", "carac": "sagesse", "couleur": "bleu"},
    {"nom": "Plan du reseau", "type": "max", "carac": "sagesse", "couleur": "bleu"},
    {"nom": "Frappe premeditee", "type": "somme", "caracs": ("sagesse", "force"), "couleur": "bleu"},
    # --- Cartes globales : elles lisent les trois caracteristiques ---
    {"nom": "Melee generale", "type": "total", "couleur": "gris"},
    {"nom": "Coup d'eclat", "type": "meilleure", "couleur": "gris"},
    {"nom": "Maillon faible", "type": "pire", "couleur": "gris"},
]

_compteur_carte = itertools.count(1)


def caracs_utilisees(modele):
    """Les caracteristiques que la condition du modele lit reellement."""
    type_condition = modele["type"]
    if type_condition == "max":
        return (modele["carac"],)
    if type_condition == "somme":
        return tuple(modele["caracs"])
    return CARACS  # total / meilleure / pire


def libelle_condition(modele):
    """Le texte de la condition, tel qu'imprime au recto de la carte."""
    type_condition = modele["type"]
    if type_condition == "max":
        return f"{LIBELLE_CARAC[modele['carac']]} la plus haute"
    if type_condition == "somme":
        gauche, droite = modele["caracs"]
        return f"{LIBELLE_CARAC[gauche]} + {LIBELLE_CARAC[droite]} la plus haute"
    if type_condition == "total":
        return "Total des trois caracteristiques le plus haut"
    if type_condition == "meilleure":
        return "Meilleure caracteristique la plus haute"
    return "Le joueur dont la plus petite caracteristique est la plus faible perd"


def _cle(modele, caracs):
    """Cle de comparaison d'un Combattant pour cette condition. Les cles des deux
    Combattants sont comparees dans l'ordre lexicographique : la plus grande remporte la
    bataille, l'egalite parfaite la rend nulle."""
    type_condition = modele["type"]
    if type_condition == "max":
        return (caracs[modele["carac"]],)
    if type_condition == "somme":
        return (sum(caracs[c] for c in modele["caracs"]),)
    if type_condition == "total":
        return (sum(caracs[c] for c in CARACS),)
    if type_condition == "meilleure":
        return (max(caracs[c] for c in CARACS),)
    # "pire" : la plus petite caracteristique la plus haute l'emporte, donc celui dont la
    # plus petite est la plus faible perd la bataille.
    return (min(caracs[c] for c in CARACS),)


def _valider_modeles():
    """Le deck doit rester rigoureusement symetrique entre les trois caracteristiques."""
    if len({m["nom"] for m in MODELES}) != len(MODELES):
        raise ValueError("Deux cartes Bataille portent le meme nom")
    # Chaque couleur de caracteristique doit apparaitre sur le meme nombre de cartes : aucune
    # caracteristique n'est structurellement favorisee.
    par_couleur = {couleur: 0 for couleur in COULEUR_PAR_CARAC.values()}
    par_couleur["gris"] = 0
    for modele in MODELES:
        par_couleur[modele["couleur"]] += 1
    couleurs_caracs = set(COULEUR_PAR_CARAC.values())
    if len({par_couleur[c] for c in couleurs_caracs}) != 1:
        raise ValueError(f"Couleurs inegalement reparties : {par_couleur}")


_valider_modeles()


class CarteBataille:
    def __init__(self, modele):
        self.id = next(_compteur_carte)
        self.modele = modele
        self.nom = modele["nom"]
        self.couleur = modele["couleur"]

    def resoudre(self, caracs_j1, caracs_j2):
        """Retourne "j1", "j2", ou None si la bataille est nulle."""
        cle_j1 = _cle(self.modele, caracs_j1)
        cle_j2 = _cle(self.modele, caracs_j2)
        if cle_j1 > cle_j2:
            return "j1"
        if cle_j2 > cle_j1:
            return "j2"
        return None

    def detail(self, caracs):
        """Les caracteristiques lues par la condition, pour tracer la resolution."""
        return [(LIBELLE_CARAC[carac], caracs[carac]) for carac in caracs_utilisees(self.modele)]

    def to_dict(self, revele=True):
        """Aucune information n'est transmise tant que la carte n'est pas revelee : ni
        nom, ni condition, ni couleur."""
        data = {"id": self.id, "revele": revele}
        if revele:
            data["nom"] = self.nom
            data["condition"] = libelle_condition(self.modele)
            data["caracs_lues"] = list(caracs_utilisees(self.modele))
            data["couleur"] = self.couleur
        return data


def construire_deck():
    """Les cartes du deck, melangees."""
    deck = [CarteBataille(modele) for modele in MODELES]
    random.shuffle(deck)
    return deck


def catalogue():
    """Composition du deck, pour la legende du frontend."""
    return [
        {
            "nom": modele["nom"],
            "condition": libelle_condition(modele),
            "couleur": modele["couleur"],
            "caracs_lues": list(caracs_utilisees(modele)),
        }
        for modele in MODELES
    ]


class Deck:
    """La pioche unique de cartes Bataille, commune aux deux joueurs et persistante pour
    toute la partie (les 4 duels) : elle n'est remelangee que lorsqu'elle est epuisee et
    qu'il faut encore piocher, jamais entre deux duels. Les cartes sont revelees a
    l'aveugle, sans aucune information avant reveal ; `compteurs` suit, par couleur, le
    nombre de cartes deja sorties depuis le dernier remelange."""

    def __init__(self):
        self._remplir()

    def _remplir(self):
        self.cartes = construire_deck()
        self.compteurs = {"rouge": 0, "vert": 0, "bleu": 0, "gris": 0}

    def piocher(self):
        """Retire et retourne la carte du dessus de la pioche ; la remelange d'abord si
        elle est epuisee."""
        if not self.cartes:
            self._remplir()
        carte = self.cartes.pop()
        self.compteurs[carte.couleur] += 1
        return carte

    def cartes_restantes(self):
        return len(self.cartes)
