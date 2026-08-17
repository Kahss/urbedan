"""Heuristique de choix de l'IA : quel Combattant engager sur le champ de bataille du duel.

Au moment d'engager son Combattant, l'IA ne connait que le dos de la carte : la couleur
des 3 cases. Elle n'a acces ni aux valeurs du recto, ni a la presence d'Energie — pas
plus que le joueur humain. Elle procede donc par esperance :

1. elle enumere les faces du deck dont le dos correspond a celui revele. La composition
   du deck est publique (elle est affichee en legende dans l'interface), mais l'IA ne
   tient volontairement pas compte des cartes deja jouees dans la partie : elle ne compte
   pas les cartes, exactement comme un joueur qui ne les memoriserait pas.
2. pour chaque face possible et chaque Combattant candidat, elle resout reellement le
   duel avec le moteur de `powers.py`, sur des Joueurs fictifs, et mesure l'ecart de PV
   qui en resulte. Elle n'a donc pas besoin d'approximer les Pouvoirs : Victoire,
   Surpuissance, Contrecoup, Stop pouvoir, Echange... sont evalues exactement, mais sur
   une carte hypothetique.
3. elle retient le Combattant dont l'ecart de PV moyen sur ces faces est le meilleur.

L'information disponible depend du role, et l'IA en tient compte :
- en J2, elle connait le Combattant deja engage par J1 : elle evalue directement sa
  reponse.
- en J1, elle ne le connait pas. Les equipes etant face visible, elle suppose que
  l'adversaire repondra au mieux (minimax a un coup) et retient le Combattant dont la
  meilleure reponse adverse coute le moins cher.

Les egalites sont tranchees au hasard pour eviter un jeu totalement previsible.
"""
import random
from collections import defaultdict

from .champs import ChampDeBataille, faces_du_deck
from .powers import resoudre_duel


class _JoueurFictif:
    """Joueur jetable : sert uniquement de support aux PV pendant la resolution d'un duel
    hypothetique, sans jamais toucher a l'etat de la partie."""

    __slots__ = ("nom", "pv", "est_ia", "equipe")

    def __init__(self, nom, pv):
        self.nom = nom
        self.pv = pv
        self.est_ia = True
        self.equipe = []


def _indexer_par_dos():
    index = defaultdict(list)
    for nom, cases in faces_du_deck():
        champ = ChampDeBataille(nom, cases)
        index[tuple(champ.dos())].append(champ)
    return dict(index)


_FACES_PAR_DOS = _indexer_par_dos()


def champs_possibles(dos):
    """Les faces du deck compatibles avec le dos revele."""
    return _FACES_PAR_DOS.get(tuple(dos), [])


def _ecart_pv(instance_j1, instance_j2, champ, duel_numero, duels_max, pv_j1, pv_j2):
    """Resout un duel hypothetique sur `champ` et retourne l'ecart de PV (J1 - J2) qu'il
    produit."""
    fictif_j1 = _JoueurFictif("j1", pv_j1)
    fictif_j2 = _JoueurFictif("j2", pv_j2)
    resoudre_duel(fictif_j1, instance_j1, fictif_j2, instance_j2, champ, duel_numero, duels_max)
    return (fictif_j1.pv - pv_j1) - (fictif_j2.pv - pv_j2)


def _esperance(instance, instance_adverse, role, champs, duel_numero, duels_max, pv_soi, pv_adv):
    """Ecart de PV moyen, en notre faveur, sur l'ensemble des faces encore possibles."""
    total = 0
    for champ in champs:
        if role == "j1":
            total += _ecart_pv(instance, instance_adverse, champ, duel_numero, duels_max, pv_soi, pv_adv)
        else:
            total -= _ecart_pv(instance_adverse, instance, champ, duel_numero, duels_max, pv_adv, pv_soi)
    return total / len(champs)


def choisir_combattant(joueur, adversaire, role, duel_numero, duels_max, dos, combattant_adverse=None):
    """Choisit le Combattant a engager. `combattant_adverse` est fourni quand le joueur
    est J2 (le Combattant de J1 est deja sur la table), None quand il est J1."""
    candidats = joueur.combattants_disponibles()
    champs = champs_possibles(dos)
    reponses = adversaire.combattants_disponibles()
    if len(candidats) == 1 or not champs or (combattant_adverse is None and not reponses):
        return random.choice(candidats)

    contexte = (duel_numero, duels_max, joueur.pv, adversaire.pv)
    scores = []
    for instance in candidats:
        if combattant_adverse is not None:
            score = _esperance(instance, combattant_adverse, role, champs, *contexte)
        else:
            # J1 ne sait pas ce qu'on lui opposera : il retient l'hypothese la plus
            # defavorable, celle ou l'adversaire repond au mieux.
            score = min(
                _esperance(instance, reponse, role, champs, *contexte) for reponse in reponses
            )
        scores.append((score, instance))

    meilleur = max(score for score, _ in scores)
    return random.choice([instance for score, instance in scores if score == meilleur])
