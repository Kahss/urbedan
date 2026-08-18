"""Cartes Bataille : la resolution d'un duel se fait en remportant 3 batailles.

Un Combattant n'a plus de Puissance mais trois caracteristiques, chacune de 0 a 5 :
Force (rouge), Dexterite (vert), Sagesse (bleu). Une carte Bataille porte au recto une
condition qui designe le vainqueur de la bataille a partir de ces caracteristiques ; si
la condition ne separe pas les deux Combattants, la bataille est nulle et personne ne
marque.

Le dos d'une carte porte **une seule couleur**, choisie parmi les caracteristiques que
sa condition utilise : c'est l'unique information disponible avant de piocher. L'indice
est donc partiel et parfois trompeur — un dos rouge annonce le plus souvent "Force la
plus haute", mais peut aussi cacher "Force la plus basse", une somme ou un departage ou
la Force n'est que secondaire.

Le deck compte 21 cartes distinctes, structurees de facon symetrique : chaque
caracteristique est la caracteristique principale de 6 cartes (3 "la plus haute", 1 "la
plus basse", 1 somme avec la suivante, 1 departage par la suivante), auxquelles
s'ajoutent 3 cartes globales qui lisent les trois caracteristiques. Aucune
caracteristique n'est donc structurellement meilleure qu'une autre, et les dos se
repartissent exactement en 7 rouges, 7 verts et 7 bleus.
"""
import itertools
import random

# Les trois caracteristiques, dans l'ordre d'affichage, et leur couleur.
CARACS = ("force", "dexterite", "sagesse")
COULEUR_PAR_CARAC = {"force": "rouge", "dexterite": "vert", "sagesse": "bleu"}
LIBELLE_CARAC = {"force": "Force", "dexterite": "Dexterite", "sagesse": "Sagesse"}

# Modeles de carte : nom, type de condition et caracteristiques lues, couleur du dos.
# Les types de condition :
#   max              : la caracteristique la plus haute l'emporte
#   min              : la plus basse l'emporte
#   somme            : la somme de deux caracteristiques la plus haute l'emporte
#   max_departage    : la plus haute l'emporte ; a egalite, une seconde caracteristique
#   total            : le total des trois caracteristiques le plus haut l'emporte
#   meilleure        : la meilleure des trois caracteristiques la plus haute l'emporte
#   pire             : celui dont la plus petite des trois caracteristiques est la plus
#                      faible perd la bataille (donc : la plus petite la plus haute gagne)
# Les caracteristiques tournent en cycle (force -> dexterite -> sagesse -> force) pour
# que les trois groupes de 6 cartes soient rigoureusement equivalents.
MODELES = [
    # --- Force (rouge) : somme avec Dexterite, departage par Sagesse ---
    {"nom": "Bras de fer", "type": "max", "carac": "force", "verso": "rouge"},
    {"nom": "Mur porteur", "type": "max", "carac": "force", "verso": "rouge"},
    {"nom": "Rideau de fer", "type": "max", "carac": "force", "verso": "rouge"},
    {"nom": "Passage etroit", "type": "min", "carac": "force", "verso": "rouge"},
    {"nom": "Escalade sauvage", "type": "somme", "caracs": ("force", "dexterite"), "verso": "vert"},
    {"nom": "Poigne et sang-froid", "type": "max_departage", "carac": "force", "departage": "sagesse", "verso": "bleu"},
    # --- Dexterite (vert) : somme avec Sagesse, departage par Force ---
    {"nom": "Toits mouilles", "type": "max", "carac": "dexterite", "verso": "vert"},
    {"nom": "Slalom de beton", "type": "max", "carac": "dexterite", "verso": "vert"},
    {"nom": "Cable tendu", "type": "max", "carac": "dexterite", "verso": "vert"},
    {"nom": "Piege a reflexes", "type": "min", "carac": "dexterite", "verso": "vert"},
    {"nom": "Ligne de fuite", "type": "somme", "caracs": ("dexterite", "sagesse"), "verso": "bleu"},
    {"nom": "Cavale sur les toits", "type": "max_departage", "carac": "dexterite", "departage": "force", "verso": "rouge"},
    # --- Sagesse (bleu) : somme avec Force, departage par Dexterite ---
    {"nom": "Lecture du quartier", "type": "max", "carac": "sagesse", "verso": "bleu"},
    {"nom": "Signal brouille", "type": "max", "carac": "sagesse", "verso": "bleu"},
    {"nom": "Plan du reseau", "type": "max", "carac": "sagesse", "verso": "bleu"},
    {"nom": "Exces de prudence", "type": "min", "carac": "sagesse", "verso": "bleu"},
    {"nom": "Frappe premeditee", "type": "somme", "caracs": ("sagesse", "force"), "verso": "rouge"},
    {"nom": "Bluff dans l'impasse", "type": "max_departage", "carac": "sagesse", "departage": "dexterite", "verso": "vert"},
    # --- Cartes globales : elles lisent les trois caracteristiques ---
    {"nom": "Melee generale", "type": "total", "verso": "vert"},
    {"nom": "Coup d'eclat", "type": "meilleure", "verso": "bleu"},
    {"nom": "Maillon faible", "type": "pire", "verso": "rouge"},
]

_compteur_carte = itertools.count(1)


def caracs_utilisees(modele):
    """Les caracteristiques que la condition du modele lit reellement."""
    type_condition = modele["type"]
    if type_condition in ("max", "min"):
        return (modele["carac"],)
    if type_condition == "somme":
        return tuple(modele["caracs"])
    if type_condition == "max_departage":
        return (modele["carac"], modele["departage"])
    return CARACS  # total / meilleure


def libelle_condition(modele):
    """Le texte de la condition, tel qu'imprime au recto de la carte."""
    type_condition = modele["type"]
    if type_condition == "max":
        return f"{LIBELLE_CARAC[modele['carac']]} la plus haute"
    if type_condition == "min":
        return f"{LIBELLE_CARAC[modele['carac']]} la plus basse"
    if type_condition == "somme":
        gauche, droite = modele["caracs"]
        return f"{LIBELLE_CARAC[gauche]} + {LIBELLE_CARAC[droite]} la plus haute"
    if type_condition == "max_departage":
        return (
            f"{LIBELLE_CARAC[modele['carac']]} la plus haute ; a egalite, "
            f"{LIBELLE_CARAC[modele['departage']]} la plus haute"
        )
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
    if type_condition == "min":
        return (-caracs[modele["carac"]],)
    if type_condition == "somme":
        return (sum(caracs[c] for c in modele["caracs"]),)
    if type_condition == "max_departage":
        return (caracs[modele["carac"]], caracs[modele["departage"]])
    if type_condition == "total":
        return (sum(caracs[c] for c in CARACS),)
    if type_condition == "meilleure":
        return (max(caracs[c] for c in CARACS),)
    # "pire" : la plus petite caracteristique la plus haute l'emporte, donc celui dont la
    # plus petite est la plus faible perd la bataille.
    return (min(caracs[c] for c in CARACS),)


def _valider_modeles():
    """Le dos ne peut annoncer qu'une couleur effectivement lue par la condition, et le
    deck doit rester rigoureusement symetrique entre les trois caracteristiques."""
    if len(MODELES) % len(CARACS) != 0:
        raise ValueError(f"{len(MODELES)} cartes : le deck doit etre divisible par {len(CARACS)}")
    if len({m["nom"] for m in MODELES}) != len(MODELES):
        raise ValueError("Deux cartes Bataille portent le meme nom")
    for modele in MODELES:
        couleurs_possibles = {COULEUR_PAR_CARAC[c] for c in caracs_utilisees(modele)}
        if modele["verso"] not in couleurs_possibles:
            raise ValueError(
                f"{modele['nom']} : le dos {modele['verso']} n'est pas une couleur lue par la condition"
            )
    # Chaque type de condition doit se repartir identiquement entre les trois caracs.
    for type_condition in ("max", "min"):
        par_carac = {carac: 0 for carac in CARACS}
        for modele in MODELES:
            if modele["type"] == type_condition:
                par_carac[modele["carac"]] += 1
        if len(set(par_carac.values())) != 1:
            raise ValueError(f"Conditions '{type_condition}' inegalement reparties : {par_carac}")
    # Chaque couleur doit apparaitre au dos du meme nombre de cartes : le choix d'une
    # pioche plutot que l'autre ne doit favoriser aucune caracteristique a priori.
    par_couleur = {couleur: 0 for couleur in COULEUR_PAR_CARAC.values()}
    for modele in MODELES:
        par_couleur[modele["verso"]] += 1
    if len(set(par_couleur.values())) != 1:
        raise ValueError(f"Dos inegalement repartis : {par_couleur}")


_valider_modeles()


class CarteBataille:
    def __init__(self, modele):
        self.id = next(_compteur_carte)
        self.modele = modele
        self.nom = modele["nom"]
        self.verso = modele["verso"]

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
        """Le dos est toujours transmis ; le recto (nom, condition) ne l'est qu'une fois
        la carte revelee, jamais tant qu'elle dort au sommet d'une pioche."""
        data = {"id": self.id, "verso": self.verso, "revele": revele}
        if revele:
            data["nom"] = self.nom
            data["condition"] = libelle_condition(self.modele)
            data["caracs_lues"] = list(caracs_utilisees(self.modele))
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
            "verso": modele["verso"],
            "caracs_lues": list(caracs_utilisees(modele)),
        }
        for modele in MODELES
    ]


class Pioches:
    """Les 2 pioches de cartes Bataille posees au centre de la table. Le deck complet est
    melange puis coupe en deux au debut de chaque duel : chaque duel repart donc du meme
    ensemble de cartes, sans memoire de celles sorties au duel precedent. A son tour, un
    joueur choisit l'une des deux pioches, en ne connaissant que la couleur au dos de sa
    carte du dessus. Un duel ne pouvant reveler que 7 cartes, une pioche ne peut pas
    s'epuiser en cours de duel."""

    def __init__(self):
        self.piles = [[], []]
        self.remelanger()

    def remelanger(self):
        """Reconstitue les deux pioches a partir du deck complet melange."""
        deck = construire_deck()
        coupe = len(deck) // 2
        self.piles = [deck[:coupe], deck[coupe:]]

    def sommets(self):
        """La carte du dessus de chaque pioche (None si la pioche est vide)."""
        return [pile[-1] if pile else None for pile in self.piles]

    def piocher(self, index):
        """Retire et retourne la carte du dessus de la pioche demandee."""
        if index not in (0, 1):
            raise IndexError("Pioche inconnue")
        if not self.piles[index]:
            raise IndexError("Pioche vide")
        return self.piles[index].pop()

    def cartes_en_pioche(self):
        """Les cartes encore endormies dans les deux pioches, toutes pioches confondues.
        Leur liste est une information publique (le deck est connu et les cartes revelees
        pendant le duel sont visibles de tous) : seule leur repartition entre les deux
        pioches est cachee."""
        return [carte for pile in self.piles for carte in pile]
