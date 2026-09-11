"""Heuristiques de l'IA : quel Combattant jouer pour la manche en cours, puis,
pendant la phase de pioche "stop ou encore", piocher une Carte Puissance ou s'arreter.

Choix du Combattant (`choisir_combattant`) :
Remplace un tirage purement aleatoire par une estimation simple de la Puissance
totale (puis, en cas d'egalite, des Degats, puis de la Vie) que produirait chaque
Combattant disponible, en ne comptant que ce qui est certain au moment du choix :
- Courage / Riposte / Vengeance / Domination sont verifiables immediatement (role du
  duel, PV courants). Victoire / Defaite / Contrecoup dependent de l'issue du duel,
  inconnue au moment du choix : ils ne sont jamais comptes. 3+ depend du nombre de
  Cartes Puissance qui seront piochees, inconnu au moment du choix : il n'est jamais
  compte non plus.
- Patience / Impatience sont calculables directement (numero du duel). Par carte /
  Par carte adverse / Par carte en jeu dependent du nombre de Cartes Puissance qui
  seront piochees pendant la phase de pioche a venir, inconnu au moment de choisir
  son Combattant : ils sont estimes avec un nombre moyen de cartes (`NB_CARTES_MOYEN_ESTIME`),
  plafonne comme en resolution reelle.
- Stop pouvoir / Copie pouvoir / Protection / Echange dependent trop du Combattant
  adverse (inconnu) pour etre estimes utilement : ils ne modifient pas le score.

Decision de pioche (`decider_piocher_ou_arreter`) :
A chaque tour, l'IA calcule l'esperance de gain d'un tirage supplementaire a partir
de la composition exacte du tas restant (connue, puisque le tas est un jeu fini de
Cartes Puissance) :
- p_bust = proportion des cartes restantes qui feraient passer son malus total a 3
  ou plus (ce qui annulerait toute la puissance deja accumulee par ses cartes) ;
- gain_moyen = puissance moyenne des cartes restantes qui ne feraient pas bust ;
- EV(piocher) = p_bust * (-puissance_cartes_actuelle) + (1 - p_bust) * gain_moyen.
Elle pioche si cette esperance est strictement positive, s'arrete sinon. Heuristique
simple, ajustable ulterieurement.
"""
import random

NB_CARTES_MOYEN_ESTIME = 2
PLAFOND_CARTES_PAR_DEFAUT = 3


def _condition_certaine(condition, role, pv_soi, pv_adv):
    """True/False si la condition est verifiable des maintenant, None si elle depend de
    l'issue du duel (inconnue au moment du choix)."""
    if condition is None:
        return True
    if condition == "courage":
        return role == "j1"
    if condition == "riposte":
        return role == "j2"
    if condition == "vengeance":
        return pv_adv > pv_soi
    if condition == "domination":
        return pv_adv < pv_soi
    return None  # victoire / defaite / 3+


def _estimer_gain(pouvoir, role, duel_numero, duels_max, pv_soi, pv_adv):
    """Estime (gain_puissance, gain_degats, gain_vie) qu'apporterait `pouvoir` (toujours
    actif dans cette version), a partir des seules informations connues avant la pioche."""
    if pouvoir is None:
        return 0, 0, 0

    if _condition_certaine(pouvoir.get("condition"), role, pv_soi, pv_adv) is not True:
        return 0, 0, 0

    modificateur = pouvoir.get("modificateur")
    if modificateur == "contrecoup":
        return 0, 0, 0  # ne se declenche qu'en cas de victoire, inconnue au moment du choix

    plafond = pouvoir.get("plafond_cartes", PLAFOND_CARTES_PAR_DEFAUT)

    def valeur_effective(valeur):
        if modificateur == "par_carte":
            return valeur * min(NB_CARTES_MOYEN_ESTIME, plafond)
        if modificateur == "par_carte_adverse":
            return valeur * min(NB_CARTES_MOYEN_ESTIME, plafond)
        if modificateur == "par_carte_en_jeu":
            return valeur * min(2 * NB_CARTES_MOYEN_ESTIME, plafond)
        if modificateur == "patience":
            return valeur * (duel_numero - 1)
        if modificateur == "impatience":
            return valeur * (duels_max - duel_numero)
        return valeur

    gain_puissance = gain_degats = gain_vie = 0.0
    for effet in pouvoir.get("effets", []):
        cible_soi = effet.get("cible", "soi") == "soi"
        if effet["type"] == "puissance":
            valeur = valeur_effective(effet.get("valeur", 0))
            gain_puissance += valeur if cible_soi else -valeur
        elif effet["type"] == "degats":
            if cible_soi:
                gain_degats += valeur_effective(effet.get("valeur", 0))
        elif effet["type"] == "vampirisme":
            x = valeur_effective(effet.get("valeur", 0))
            gain_vie += 2 * x  # -x cote adverse, +x cote soi : ecart net de 2x

    return gain_puissance, gain_degats, gain_vie


def choisir_combattant(joueur, role, duel_numero, duels_max, pv_soi, pv_adv):
    """Choisit, parmi les Combattants disponibles du joueur, celui qui maximise la
    Puissance totale estimee pour ce duel (puis les Degats, puis la Vie, en cas
    d'egalite). Retourne l'instance de Combattant choisie."""
    combinaisons = []
    for instance in joueur.combattants_disponibles():
        gain_puissance, gain_degats, gain_vie = _estimer_gain(
            instance.template.pouvoir, role, duel_numero, duels_max, pv_soi, pv_adv
        )
        puissance_totale = instance.template.puissance + gain_puissance
        degats_totaux = instance.template.degats + gain_degats
        score = (puissance_totale, degats_totaux, gain_vie)
        combinaisons.append((score, instance))

    meilleur_score = max(score for score, _ in combinaisons)
    meilleures = [c for c in combinaisons if c[0] == meilleur_score]
    _, instance = random.choice(meilleures)
    return instance


def decider_piocher_ou_arreter(cartes_actuelles, malus_actuel, deck_restant):
    """Decide, a partir des cartes deja piochees et de la composition exacte du tas
    restant, s'il faut piocher ("piocher") ou s'arreter ("arreter")."""
    if not deck_restant:
        return "arreter"

    puissance_cartes_actuelle = 0 if malus_actuel >= 3 else sum(c.puissance for c in cartes_actuelles)

    nb_total = len(deck_restant)
    nb_bust = sum(1 for c in deck_restant if malus_actuel + c.malus >= 3)
    p_bust = nb_bust / nb_total

    cartes_sans_bust = [c for c in deck_restant if malus_actuel + c.malus < 3]
    gain_moyen = (sum(c.puissance for c in cartes_sans_bust) / len(cartes_sans_bust)) if cartes_sans_bust else 0

    esperance_piocher = p_bust * (-puissance_cartes_actuelle) + (1 - p_bust) * gain_moyen
    return "piocher" if esperance_piocher > 0 else "arreter"
