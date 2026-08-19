"""Heuristique de choix de l'IA : quel Combattant engager, et surtout quelle pioche de
cartes Bataille choisir a chaque tour.

- **Combattant** : tire au hasard parmi ceux encore disponibles. L'IA ne contre-choisit
  pas le Combattant adverse (cf. instructions.md).
- **Pioche** : c'est la seule decision reellement informee du duel. L'IA ne connait de
  chaque pioche que la couleur au dos de sa carte du dessus, mais elle connait la
  composition du deck et voit les cartes deja revelees : elle sait donc exactement
  quelles cartes dorment encore dans les deux pioches, sans savoir laquelle est ou. Pour
  chaque pioche, elle passe en revue les cartes encore en jeu dont le dos porte cette
  couleur, resout chacune contre les caracteristiques des deux Combattants engages (celles
  du duel, une couleur eventuellement annulee par une capacite) et l'Initiative eventuelle
  des deux camps, puis retient la pioche dont l'esperance est la meilleure (+1 bataille
  gagnee, -1 perdue, 0 nulle). Les egalites sont tranchees au hasard pour eviter un jeu
  previsible.
"""
import random


def choisir_combattant(joueur):
    """Choisit au hasard un Combattant parmi ceux qui n'ont pas encore combattu."""
    return random.choice(joueur.combattants_disponibles())


def _esperance_pioche(
    verso, cartes_en_pioche, caracs_soi, caracs_adv, role_soi,
    initiative_soi=False, initiative_adv=False,
):
    """Esperance de gain (en batailles) d'une pioche dont le dos annonce `verso`, sur
    l'ensemble des cartes encore en jeu portant cette couleur."""
    candidates = [carte for carte in cartes_en_pioche if carte.verso == verso]
    if not candidates:
        return 0.0
    role_adv = "j2" if role_soi == "j1" else "j1"
    caracs_j1 = caracs_soi if role_soi == "j1" else caracs_adv
    caracs_j2 = caracs_adv if role_soi == "j1" else caracs_soi
    total = 0
    for carte in candidates:
        gagnant = carte.resoudre(caracs_j1, caracs_j2)
        # Une bataille nulle est remportee par le camp qui a l'Initiative (capacite) ; si
        # les deux l'ont, elles se neutralisent.
        if gagnant is None and initiative_soi != initiative_adv:
            gagnant = role_soi if initiative_soi else role_adv
        if gagnant == role_soi:
            total += 1
        elif gagnant == role_adv:
            total -= 1
    return total / len(candidates)


def choisir_pioche(
    sommets, cartes_en_pioche, caracs_soi, caracs_adv, role_soi,
    initiative_soi=False, initiative_adv=False,
):
    """Retourne l'index (0 ou 1) de la pioche a choisir. `sommets` donne la carte du
    dessus de chaque pioche : seule sa couleur de dos est exploitee."""
    scores = []
    for index, sommet in enumerate(sommets):
        if sommet is None:
            continue
        esperance = _esperance_pioche(
            sommet.verso, cartes_en_pioche, caracs_soi, caracs_adv, role_soi,
            initiative_soi, initiative_adv,
        )
        scores.append((esperance, index))
    if not scores:
        raise IndexError("Aucune pioche disponible")
    meilleure = max(esperance for esperance, _ in scores)
    return random.choice([index for esperance, index in scores if esperance == meilleure])
