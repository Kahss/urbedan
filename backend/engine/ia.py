"""Heuristique de draft de l'IA (version Eredice).

A son creneau, l'IA evalue toutes les actions possibles -- chaque De encore dans le pool
x chacun de ses 3 Personnages x les deux usages possibles (stocker la ressource ou
depenser le De pour l'attaque de base) -- et retient la meilleure selon une estimation
simple, exprimee en "PV equivalents" :

- attaque de base : la valeur d'Attaque courante du Personnage (avec une prime enorme si
  elle acheve l'adversaire) ;
- stocker : si le De declenche immediatement une Capacite, la valeur estimee de cette
  Capacite ; sinon, une fraction de la valeur de la Capacite dont il rapproche le
  Personnage (0 si le De n'avance aucune Capacite).

L'estimation ne regarde qu'un coup a l'avance (pas de simulation des cascades ni de la
reponse adverse) : suffisant pour un POC et pour faire tourner les simulations
d'equilibrage. Les egalites sont tranchees au hasard afin que le jeu ne soit pas
totalement previsible.
"""
import random
from collections import Counter

from .capacites import trouver_paiement
from .models import PV_DEPART, De

# Valeur d'un point d'effet, exprimee en PV equivalents.
POIDS_EFFETS = {
    "degats": 1.0,
    "soin": 0.8,
    "vampirisme": 1.8,
    "attaque": 2.0,       # gain permanent : vaut plusieurs rounds d'attaques
    "initiative": 0.8,
    "de_bonus": 2.0,
    "de_cree": 2.0,
    "de_vole": 2.5,       # prend une ressource a l'adversaire et l'ajoute a la sienne
    "de_defausse": 1.5,
    "relance_pool": 0.5,
}

# Une condition d'etat actuellement fausse peut redevenir vraie : la Capacite n'est pas
# sans valeur, mais elle est incertaine.
DECOTE_CONDITION = 0.4
# Condition dependant du paiement exact (monochrome / polychrome) : incertaine.
DECOTE_PAIEMENT = 0.8
# Un De qui ne fait que rapprocher d'une Capacite non encore acquise : risque de ne
# jamais la completer.
DECOTE_PROGRESSION = 0.85
# Nombre d'attaques reellement converties, par round, par une equipe de 3 Personnages.
FACTEUR_CIBLE_EQUIPE = 1.5


def _multiplicateur_estime(capacite, perso, partie, nb_des):
    mod = capacite.get("multiplicateur")
    if mod == "par_de":
        return nb_des
    if mod == "patience":
        return partie.round_numero
    if mod == "par_perso_charge":
        return max(1, sum(1 for p in perso.joueur.equipe if p.des_stockes))
    return 1


def _valeur_effet(effet, perso, partie, mult):
    type_effet = effet["type"]
    poids = POIDS_EFFETS.get(type_effet, 0.5)
    if type_effet in ("degats", "soin", "vampirisme"):
        return effet.get("valeur", 0) * mult * poids
    if type_effet == "attaque":
        cible = effet.get("cible", "soi")
        # Un bonus/malus d'Attaque ne se convertit que si le Personnage attaque
        # effectivement : sur une equipe entiere, tous ses membres n'attaquent pas
        # chaque round (l'essentiel des Des part en Capacites). On ne compte donc pas
        # les 3 membres a plein.
        nombre = FACTEUR_CIBLE_EQUIPE if cible in ("equipe", "equipe_adverse") else 1
        signe = -1 if cible == "equipe_adverse" else 1
        return effet.get("valeur", 0) * mult * poids * nombre * signe
    if type_effet == "initiative":
        return abs(effet.get("valeur", 0)) * mult * poids
    return poids * mult


def _facteur_condition(capacite, perso, partie):
    """Decote liee a la condition de la Capacite : 1 si elle est certaine, moins sinon.

    Les conditions d'etat (`vengeance`, `domination`, `blesse`, position dans la piste)
    sont evaluables immediatement ; `monochrome` / `polychrome` dependent du paiement
    exact qui sera retenu et restent donc incertaines."""
    condition = capacite.get("condition")
    if condition is None:
        return 1.0
    if condition in ("monochrome", "polychrome"):
        return DECOTE_PAIEMENT
    joueur = perso.joueur
    adversaire = partie.adversaire(joueur)
    if condition == "vengeance":
        vraie = adversaire.pv > joueur.pv
    elif condition == "domination":
        vraie = adversaire.pv < joueur.pv
    elif condition == "blesse":
        vraie = joueur.pv <= PV_DEPART // 2
    elif condition == "tete_de_piste":
        vraie = partie.position_piste(perso) <= 1
    elif condition == "queue_de_piste":
        vraie = partie.position_piste(perso) >= len(partie.piste) - 2
    else:
        return 1.0
    return 1.0 if vraie else DECOTE_CONDITION


def _valeur_capacite(capacite, perso, partie, nb_des):
    mult = _multiplicateur_estime(capacite, perso, partie, nb_des)
    return sum(_valeur_effet(e, perso, partie, mult) for e in capacite.get("effets", []))


def _manque(couleurs, cout):
    """Nombre de Des supplementaires necessaires pour payer `cout` avec `couleurs`."""
    dispo = Counter(couleurs)
    demandes = Counter(c for c in cout if c is not None)
    jokers = sum(1 for c in cout if c is None)
    couvert = 0
    for couleur, n in demandes.items():
        pris = min(dispo[couleur], n)
        dispo[couleur] -= pris
        couvert += pris
    couvert += min(sum(dispo.values()), jokers)
    return len(cout) - couvert


def _valeur_stock(perso, couleur, partie):
    """Valeur estimee du fait de stocker un De de cette couleur sur ce Personnage."""
    couleurs_avant = perso.couleurs_stockees()
    couleurs_apres = couleurs_avant + [couleur]

    temoin = De(couleur)
    perso.des_stockes.append(temoin)
    try:
        for capacite in perso.template.capacites:
            if trouver_paiement(perso, capacite, partie) is not None:
                # Declenchement immediat : le cout est paye et la condition verifiee.
                return _valeur_capacite(
                    capacite, perso, partie, len(capacite.get("cout", []))
                )
    finally:
        perso.des_stockes.remove(temoin)

    # Aucun declenchement : on valorise la progression vers la Capacite la plus proche.
    # Valeur marginale d'un De = valeur de la Capacite / nombre de Des encore manquants
    # avant celui-ci : plus la Capacite est proche, plus le De vaut cher.
    meilleure = 0.0
    for capacite in perso.template.capacites:
        cout = capacite.get("cout", [])
        if not cout:
            continue
        avant = _manque(couleurs_avant, cout)
        if _manque(couleurs_apres, cout) >= avant:
            continue  # ce De n'avance pas cette Capacite
        valeur = _valeur_capacite(capacite, perso, partie, len(cout))
        valeur *= _facteur_condition(capacite, perso, partie) * DECOTE_PROGRESSION
        meilleure = max(meilleure, valeur / avant)
    return meilleure


def choisir_action(partie, joueur):
    """Retourne (De, PersonnageEnJeu, usage) pour le creneau courant de `joueur`."""
    adversaire = partie.adversaire(joueur)
    actions = []

    for de in partie.pool:
        for perso in joueur.equipe:
            if not perso.a_attaque:
                score = float(perso.attaque)
                if perso.attaque >= adversaire.pv:
                    score += 1000.0  # coup de grace
                actions.append((score, de, perso, "attaque"))
            actions.append((_valeur_stock(perso, de.couleur, partie), de, perso, "stock"))

    meilleur = max(score for score, _, _, _ in actions)
    candidats = [a for a in actions if a[0] >= meilleur - 1e-9]
    _, de, perso, usage = random.choice(candidats)
    return de, perso, usage
