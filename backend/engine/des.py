"""Des speciaux d'Urban Eredan (version "des par personnage").

Chaque de est un de a 6 faces, chaque face portant un couple (Puissance, Energie),
note "X/Y". Il existe 3 couleurs, declinees chacune en 2 teintes :

- rouge  : oriente Puissance (aucune Energie)
- bleu   : oriente Energie (peu de Puissance)
- violet : melange des deux
- clair  : valeurs plutot faibles ; fonce : valeurs plus elevees

Le code couleur/teinte sert de lecture rapide : la couleur annonce le type de
ressource attendu, la teinte la quantite. Les repartitions de faces sont choisies pour
limiter la variance (valeurs proches et repetees) tout en gardant un resultat aleatoire.
"""
import random

# Definition des 6 faces de chaque de, sous forme de couples (puissance, energie).
FACES_PAR_DE = {
    "rouge_clair": [(3, 0), (3, 0), (2, 0), (2, 0), (1, 0), (1, 0)],
    "rouge_fonce": [(5, 0), (5, 0), (4, 0), (4, 0), (2, 0), (2, 0)],
    "bleu_clair": [(1, 1), (1, 1), (0, 1), (0, 1), (0, 1), (0, 1)],
    "bleu_fonce": [(3, 1), (3, 1), (1, 2), (1, 2), (0, 2), (0, 2)],
    "violet_clair": [(2, 0), (2, 0), (1, 1), (1, 1), (1, 0), (0, 1)],
    "violet_fonce": [(4, 1), (4, 0), (3, 1), (3, 0), (2, 0), (1, 1)],
}

LIBELLES_DE = {
    "rouge_clair": "Rouge clair",
    "rouge_fonce": "Rouge fonce",
    "bleu_clair": "Bleu clair",
    "bleu_fonce": "Bleu fonce",
    "violet_clair": "Violet clair",
    "violet_fonce": "Violet fonce",
}


class DeInconnu(Exception):
    pass


def valider_de(type_de):
    if type_de not in FACES_PAR_DE:
        raise DeInconnu(f"Type de de inconnu : {type_de}")
    return type_de


def couleur(type_de):
    return type_de.split("_")[0]


def teinte(type_de):
    return type_de.split("_")[1]


def moyennes(type_de):
    """(Puissance moyenne, Energie moyenne) d'un de, utilisees par l'IA et l'affichage."""
    faces = FACES_PAR_DE[type_de]
    return (
        sum(p for p, _ in faces) / len(faces),
        sum(e for _, e in faces) / len(faces),
    )


def lancer(types_de):
    """Lance la liste de des donnee et retourne la liste des resultats, chacun sous la
    forme {"type", "libelle", "couleur", "teinte", "puissance", "energie"}."""
    resultats = []
    for type_de in types_de:
        puissance, energie = random.choice(FACES_PAR_DE[valider_de(type_de)])
        resultats.append({
            "type": type_de,
            "libelle": LIBELLES_DE[type_de],
            "couleur": couleur(type_de),
            "teinte": teinte(type_de),
            "puissance": puissance,
            "energie": energie,
        })
    return resultats


def de_to_dict(type_de):
    """Description statique d'un de, pour affichage sur une carte Combattant."""
    puissance_moyenne, energie_moyenne = moyennes(type_de)
    return {
        "type": type_de,
        "libelle": LIBELLES_DE[type_de],
        "couleur": couleur(type_de),
        "teinte": teinte(type_de),
        "faces": [{"puissance": p, "energie": e} for p, e in FACES_PAR_DE[type_de]],
        "puissance_moyenne": round(puissance_moyenne, 2),
        "energie_moyenne": round(energie_moyenne, 2),
    }


def catalogue():
    """Tous les types de des, pour la legende affichee dans l'interface."""
    return [de_to_dict(type_de) for type_de in FACES_PAR_DE]
