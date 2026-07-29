"""Heuristique de choix de l'IA : quel Combattant jouer, et quel Glyphe de sa main lui
associer, pour la manche en cours.

Remplace un tirage purement aleatoire par une estimation simple de la Puissance totale
(puis, en cas d'egalite, des Degats, puis de la Vie) que produirait chaque combinaison
Combattant disponible / Glyphe en main, en ne comptant que ce qui est certain au moment
du choix :
- Courage / Riposte / Vengeance / Domination sont verifiables immediatement (role du
  duel, PV courants). Victoire / Defaite / Surpuissance / Contrecoup dependent de
  l'issue du duel, inconnue au moment du choix : ils ne sont jamais comptes.
- Patience / Impatience / Par energie sont calculables directement. Par energie
  adverse / Par energie en jeu utilisent l'Energie moyenne d'un Glyphe pioche au hasard
  (l'Energie reellement jouee par l'adversaire n'est pas connue avant la resolution).
- Stop pouvoir / Copie pouvoir / Protection / Echange dependent trop du Combattant et
  du Glyphe adverses (inconnus) pour etre estimes utilement : ils ne modifient pas le
  score (l'IA ne les recherche ni ne les evite specifiquement).

L'IA choisit la combinaison de meilleur score ; les egalites sont tranchees au hasard
pour eviter un jeu totalement previsible.
"""
import random

from .models import GLYPH_DISTRIBUTION

_TOTAL_CARTES = sum(quantite for _, _, quantite in GLYPH_DISTRIBUTION)
ENERGIE_MOYENNE_GLYPHE = sum(energie * quantite for _, energie, quantite in GLYPH_DISTRIBUTION) / _TOTAL_CARTES


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
    return None  # victoire / defaite / surpuissance


def _estimer_gain(pouvoir, energie_jouee, role, duel_numero, duels_max, pv_soi, pv_adv):
    """Estime (gain_puissance, gain_degats, gain_vie) si `pouvoir` est joue avec
    `energie_jouee`, a partir des seules informations connues avant la resolution."""
    if pouvoir is None or energie_jouee < pouvoir.get("energie_min", 0):
        return 0, 0, 0

    if _condition_certaine(pouvoir.get("condition"), role, pv_soi, pv_adv) is not True:
        return 0, 0, 0

    modificateur = pouvoir.get("modificateur")
    if modificateur == "contrecoup":
        return 0, 0, 0  # ne se declenche qu'en cas de victoire, inconnue au moment du choix

    def valeur_effective(valeur):
        if modificateur == "par_energie":
            return valeur * energie_jouee
        if modificateur == "par_energie_adverse":
            return valeur * ENERGIE_MOYENNE_GLYPHE
        if modificateur == "par_energie_en_jeu":
            return valeur * (energie_jouee + ENERGIE_MOYENNE_GLYPHE)
        if modificateur == "patience":
            return valeur * duel_numero
        if modificateur == "impatience":
            return valeur * (duels_max - duel_numero + 1)
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


def choisir_combattant_et_glyphe(joueur, role, duel_numero, duels_max, pv_soi, pv_adv):
    """Choisit, parmi les Combattants disponibles et les Glyphes en main du joueur, la
    combinaison qui maximise la Puissance totale estimee pour ce duel (puis les Degats,
    puis la Vie, en cas d'egalite). Retourne (instance_combattant, glyphe)."""
    combinaisons = []
    for instance in joueur.combattants_disponibles():
        for glyphe in joueur.main_glyphes:
            gain_puissance, gain_degats, gain_vie = _estimer_gain(
                instance.template.pouvoir, glyphe.energie, role, duel_numero, duels_max, pv_soi, pv_adv
            )
            puissance_totale = instance.template.puissance + glyphe.puissance + gain_puissance
            degats_totaux = instance.template.degats + gain_degats
            score = (puissance_totale, degats_totaux, gain_vie)
            combinaisons.append((score, instance, glyphe))

    meilleur_score = max(score for score, _, _ in combinaisons)
    meilleures = [c for c in combinaisons if c[0] == meilleur_score]
    _, instance, glyphe = random.choice(meilleures)
    return instance, glyphe
