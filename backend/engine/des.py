"""Des speciaux d'Urban Eredan (version "draft de des").

Chaque de est un de a 6 faces, chaque face portant un couple (Puissance, Energie),
note "X/Y". Il existe 3 des, un par couleur :

- rouge  : oriente Puissance (aucune Energie)
- bleu   : oriente Energie (peu de Puissance, mais au moins 1 Energie garantie)
- violet : melange des deux

La couleur sert de lecture rapide : elle annonce le type de ressource que le joueur peut
s'attendre a recevoir. Les repartitions de faces sont choisies pour limiter la variance
(valeurs proches et repetees deux a deux) tout en gardant un resultat aleatoire.

Au debut de chaque duel, un pool central de 6 des est lance : toujours deux rouges, deux
bleus et deux violets (cf. COMPOSITION_POOL). Les deux joueurs y draftent ensuite leurs
3 des chacun, a tour de role.
"""
import itertools
import random

# Definition des 6 faces de chaque de, sous forme de couples (puissance, energie).
FACES_PAR_DE = {
    "rouge": [(5, 0), (5, 0), (4, 0), (4, 0), (2, 0), (2, 0)],
    "bleu": [(3, 1), (3, 1), (1, 2), (1, 2), (0, 2), (0, 2)],
    "violet": [(4, 1), (4, 0), (3, 1), (3, 0), (2, 0), (1, 1)],
}

# Composition invariable du pool central lance au debut de chaque duel.
COMPOSITION_POOL = ["rouge", "rouge", "bleu", "bleu", "violet", "violet"]

DES_PAR_JOUEUR = 3

_compteur_de = itertools.count(1)

LIBELLES_DE = {
    "rouge": "Rouge",
    "bleu": "Bleu",
    "violet": "Violet",
}


class DeInconnu(Exception):
    pass


def valider_de(type_de):
    if type_de not in FACES_PAR_DE:
        raise DeInconnu(f"Type de de inconnu : {type_de}")
    return type_de


def moyennes(type_de):
    """(Puissance moyenne, Energie moyenne) d'un de, utilisees par l'IA et l'affichage."""
    faces = FACES_PAR_DE[type_de]
    return (
        sum(p for p, _ in faces) / len(faces),
        sum(e for _, e in faces) / len(faces),
    )


def lancer(types_de):
    """Lance la liste de des donnee et retourne la liste des resultats, chacun sous la
    forme {"id", "type", "libelle", "couleur", "puissance", "energie"}. L'`id` identifie
    le de dans le pool central pour toute la duree du draft."""
    resultats = []
    for type_de in types_de:
        puissance, energie = random.choice(FACES_PAR_DE[valider_de(type_de)])
        resultats.append({
            "id": next(_compteur_de),
            "type": type_de,
            "libelle": LIBELLES_DE[type_de],
            "couleur": type_de,
            "puissance": puissance,
            "energie": energie,
        })
    return resultats


def lancer_pool():
    """Lance le pool central d'un duel : deux des de chaque couleur."""
    return lancer(COMPOSITION_POOL)


def de_to_dict(type_de):
    """Description statique d'un de, pour affichage sur une carte Combattant."""
    puissance_moyenne, energie_moyenne = moyennes(type_de)
    return {
        "type": type_de,
        "libelle": LIBELLES_DE[type_de],
        "couleur": type_de,
        "faces": [{"puissance": p, "energie": e} for p, e in FACES_PAR_DE[type_de]],
        "puissance_moyenne": round(puissance_moyenne, 2),
        "energie_moyenne": round(energie_moyenne, 2),
    }


def catalogue():
    """Tous les types de des, pour la legende affichee dans l'interface."""
    return [de_to_dict(type_de) for type_de in FACES_PAR_DE]
