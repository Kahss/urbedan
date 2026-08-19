"""Cartes bataille de la version duo (voir versions/duo.md).

Une carte bataille est revelee au debut de chaque bataille, AVANT que les joueurs ne
choisissent leur duo : son effet est donc une information publique qui determine l'enjeu
du tour. L'effet est applique par le joueur qui remporte la bataille (par les deux, en
cas de double victoire).

Chaque carte porte un `effet` (identifiant technique) et un `timing` :
- "bataille"  : modifie la resolution de la bataille en cours (avant application des Degats)
- "immediat"  : s'applique juste apres l'application des Degats
- "tour_suivant" : contraint la bataille suivante

Le deck compte un exemplaire de chaque carte, melange en debut de partie ; une seule
carte est revelee par bataille, soit 4 cartes vues par partie sur les 7 possibles.
"""
import random

BONUS_BAS_FONDS = 2
BONUS_SOIN = 2
BONUS_PLANIFICATION_PAR_BATAILLE = 1

CARTES = [
    {
        "id": "a_la_loyale",
        "nom": "À la loyale",
        "effet": "aucun",
        "timing": "aucun",
        "description": "Aucun effet : seuls les Dégâts comptent.",
    },
    {
        "id": "bas_fonds",
        "nom": "Dans les bas-fonds",
        "effet": "bas_fonds",
        "timing": "bataille",
        "description": f"Les Dégâts infligés par le vainqueur sont augmentés de {BONUS_BAS_FONDS}.",
    },
    {
        "id": "soigner_les_blesses",
        "nom": "Soigner les blessés",
        "effet": "soin",
        "timing": "immediat",
        "description": f"Le vainqueur gagne {BONUS_SOIN} PV.",
    },
    {
        "id": "reperage",
        "nom": "Repérage",
        "effet": "reperage",
        "timing": "tour_suivant",
        "description": (
            "À la bataille suivante, l'adversaire verrouille son duo en premier et révèle "
            "celui de ses 2 Combattants qu'il choisit."
        ),
    },
    {
        "id": "second_souffle",
        "nom": "Second souffle",
        "effet": "second_souffle",
        "timing": "immediat",
        "description": (
            "Le vainqueur rend une utilisation au Combattant de son équipe qu'il choisit."
        ),
    },
    {
        "id": "planification",
        "nom": "Planification",
        "effet": "planification",
        "timing": "immediat",
        "description": (
            f"Patience : le vainqueur gagne {BONUS_PLANIFICATION_PAR_BATAILLE} PV par "
            "bataille jouée, celle-ci comprise."
        ),
    },
    {
        "id": "depasser_ses_limites",
        "nom": "Dépasser ses limites",
        "effet": "depasser_ses_limites",
        "timing": "tour_suivant",
        "description": (
            "À la bataille suivante, toutes les conditions des Pouvoirs du vainqueur sont "
            "considérées comme validées."
        ),
    },
]


def construire_deck_batailles():
    deck = [dict(carte) for carte in CARTES]
    random.shuffle(deck)
    return deck


def bonus_degats(carte):
    """Bonus de Degats accorde au vainqueur par la carte bataille du tour, applique
    pendant la resolution (timing "bataille")."""
    return BONUS_BAS_FONDS if carte["effet"] == "bas_fonds" else 0


def bonus_pv(carte, tour):
    """PV gagnes par le vainqueur juste apres l'application des Degats (timing
    "immediat"). Planification porte le modificateur Patience : son gain croit avec le
    numero de la bataille."""
    if carte["effet"] == "soin":
        return BONUS_SOIN
    if carte["effet"] == "planification":
        return BONUS_PLANIFICATION_PAR_BATAILLE * tour
    return 0
