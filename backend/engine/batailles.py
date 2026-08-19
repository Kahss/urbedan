"""Cartes bataille de la version duo (voir versions/duo.md).

Une carte bataille est revelee au debut de chaque bataille, AVANT que les joueurs ne
choisissent leur duo : son effet est donc une information publique qui determine l'enjeu
du tour. L'effet est applique par le joueur qui remporte la bataille (par les deux, en
cas de double victoire).

Chaque carte porte un `effet` (identifiant technique) et un `timing` :
- "bataille"  : modifie la resolution de la bataille en cours (avant application des Degats)
- "immediat"  : s'applique juste apres l'application des Degats
- "tour_suivant" : contraint le choix des duos de la bataille suivante

Le deck compte un exemplaire de chaque carte, melange en debut de partie ; une seule
carte est revelee par bataille, soit 4 cartes vues par partie sur les 7 possibles.
"""
import random

BONUS_ACHARNEMENT = 2
BONUS_BUTIN = 2
BONUS_OVATION_PAR_COMBATTANT = 1

CARTES = [
    {
        "id": "butin",
        "nom": "Butin",
        "effet": "butin",
        "timing": "immediat",
        "description": f"Le vainqueur gagne {BONUS_BUTIN} PV.",
    },
    {
        "id": "acharnement",
        "nom": "Acharnement",
        "effet": "acharnement",
        "timing": "bataille",
        "description": f"Les Degats infliges par le vainqueur sont augmentes de {BONUS_ACHARNEMENT}.",
    },
    {
        "id": "reperage",
        "nom": "Reperage",
        "effet": "reperage",
        "timing": "tour_suivant",
        "description": (
            "A la bataille suivante, l'adversaire verrouille son duo en premier et en "
            "revele un Combattant, tire au hasard, avant que le vainqueur ne choisisse."
        ),
    },
    {
        "id": "intimidation",
        "nom": "Intimidation",
        "effet": "intimidation",
        "timing": "tour_suivant",
        "description": (
            "A la bataille suivante, l'adversaire verrouille son duo en premier et le "
            "revele entierement avant que le vainqueur ne choisisse."
        ),
    },
    {
        "id": "second_souffle",
        "nom": "Second souffle",
        "effet": "second_souffle",
        "timing": "immediat",
        "description": (
            "Les deux Combattants du duo vainqueur recuperent l'utilisation depensee "
            "pour cette bataille."
        ),
    },
    {
        "id": "ovation",
        "nom": "Ovation",
        "effet": "ovation",
        "timing": "immediat",
        "description": (
            f"Le vainqueur gagne {BONUS_OVATION_PAR_COMBATTANT} PV par Combattant de son "
            "duo engage pour la premiere fois."
        ),
    },
    {
        "id": "escarmouche",
        "nom": "Escarmouche",
        "effet": "escarmouche",
        "timing": "aucun",
        "description": "Aucun effet supplementaire : seuls les Degats comptent.",
    },
]

# Nombre de Combattants du duo que l'adversaire doit reveler, par effet d'information.
REVELATIONS = {"reperage": 1, "intimidation": 2}


def construire_deck_batailles():
    deck = [dict(carte) for carte in CARTES]
    random.shuffle(deck)
    return deck


def bonus_degats(carte):
    """Bonus de Degats accorde au vainqueur par la carte bataille du tour, applique
    pendant la resolution (timing "bataille")."""
    return BONUS_ACHARNEMENT if carte["effet"] == "acharnement" else 0
