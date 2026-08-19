"""Heuristique de l'IA, version duo : quel duo engager, et quel Combattant adverse
designer comme cible de ses effets a cible unique.

Le choix du duo se fait sur une estimation de la Puissance totale du duo, en ne comptant
que ce qui est certain au moment du choix :
- `courage` / `riposte` (role du camp, connu avant le choix puisque J1 est le vainqueur de
  la bataille precedente), `vengeance` / `domination` (PV courants), `premiere_fois` /
  `seconde_fois` (compteur d'utilisations) et `puissance_alliee` (le coequipier fait partie
  du duo evalue) sont verifiables immediatement.
- `puissance_base_adverse` / `degats_base_adverse` portent sur le duo adverse, inconnu au
  moment du choix : ils ne sont jamais comptes.
- `victoire` / `defaite` / `surpuissance` et le modificateur `contrecoup` dependent de
  l'issue de la bataille, inconnue au moment du choix : ils ne sont jamais comptes.
- `patience` / `impatience` sont calculables directement.
- `stop_pouvoir` / `copie_pouvoir` / `protection` / `echange` dependent du duo adverse
  (inconnu au moment du choix) : ils ne modifient pas le score.

Quand une carte bataille Reperage a revele un Combattant du duo adverse, l'IA ne cherche
plus a maximiser sa Puissance mais a gagner au meilleur prix : elle engage le duo legal le
moins fort qui batte encore l'estimation adverse, et si aucun ne le peut, elle sacrifie la
bataille avec son duo le plus faible pour preserver ses Combattants forts. C'est aussi ce
qui donne sa valeur a un Pouvoir conditionne par `defaite`.

Ce module porte aussi les deux choix que les cartes bataille demandent au vainqueur :
quel Combattant de son duo reveler (Reperage) et auquel de ses Combattants rendre une
utilisation (Second souffle).
"""
import random

from .powers import TYPES_CIBLE_UNIQUE, pouvoir_requiert_cible

CONDITIONS_INCERTAINES = ("victoire", "defaite", "surpuissance")


def _condition_certaine(
    pouvoir, role, n_utilisation, pv_soi, pv_adv, puissance_alliee, conditions_forcees
):
    """True/False si la condition est verifiable des maintenant, None si elle depend de
    l'issue de la bataille ou du duo adverse (inconnus au moment du choix)."""
    if conditions_forcees:
        return True
    condition = pouvoir.get("condition")
    if condition is None:
        return True
    seuil = pouvoir.get("seuil", 0)
    if condition == "puissance_alliee":
        return None if puissance_alliee is None else puissance_alliee >= seuil
    if condition in ("puissance_base_adverse", "degats_base_adverse"):
        return None  # depend du duo adverse, inconnu au moment du choix
    if condition == "courage":
        return role == "J1"
    if condition == "riposte":
        return role == "J2"
    if condition == "vengeance":
        return pv_adv > pv_soi
    if condition == "domination":
        return pv_adv < pv_soi
    if condition == "premiere_fois":
        return n_utilisation == 1
    if condition == "seconde_fois":
        return n_utilisation == 2
    return None  # victoire / defaite / surpuissance


def _valeur_effective(valeur, modificateur, tour, tours_max):
    if modificateur == "patience":
        return valeur * tour
    if modificateur == "impatience":
        return valeur * (tours_max - tour + 1)
    return valeur


def estimer_gain(
    pouvoir, role, n_utilisation, tour, tours_max, pv_soi, pv_adv,
    puissance_alliee=None, conditions_forcees=False,
):
    """Estime (gain_puissance, gain_degats, gain_vie) apporte par `pouvoir`, a partir des
    seules informations connues avant la resolution. Un malus infligé a l'adversaire
    compte comme un gain equivalent, le score etant un score d'avantage relatif."""
    if pouvoir is None:
        return 0, 0, 0
    certaine = _condition_certaine(
        pouvoir, role, n_utilisation, pv_soi, pv_adv, puissance_alliee, conditions_forcees
    )
    if certaine is not True:
        return 0, 0, 0

    modificateur = pouvoir.get("modificateur")
    if modificateur == "contrecoup":
        return 0, 0, 0  # ne se declenche qu'en cas de victoire, inconnue au moment du choix

    gain_puissance = gain_degats = gain_vie = 0.0
    for effet in pouvoir.get("effets", []):
        vers_soi = effet.get("cible", "soi") == "soi"
        valeur = _valeur_effective(effet.get("valeur", 0), modificateur, tour, tours_max)
        if effet["type"] == "puissance":
            gain_puissance += valeur if vers_soi else -valeur
        elif effet["type"] == "degats":
            # Un malus adverse retranche des Degats au duo d'en face : meme avantage
            # relatif qu'un bonus du meme montant sur le sien.
            gain_degats += valeur if vers_soi else -valeur
        elif effet["type"] == "vie":
            gain_vie += valeur if vers_soi else -valeur
        elif effet["type"] == "vampirisme":
            gain_vie += 2 * valeur  # -x cote adverse, +x cote soi : ecart net de 2x

    return gain_puissance, gain_degats, gain_vie


def _score_combattant(
    instance, role, tour, tours_max, pv_soi, pv_adv, puissance_alliee, conditions_forcees
):
    n_utilisation = instance.utilisations + 1
    gain_puissance, gain_degats, gain_vie = estimer_gain(
        instance.template.pouvoir, role, n_utilisation, tour, tours_max, pv_soi, pv_adv,
        puissance_alliee, conditions_forcees,
    )
    return (
        instance.template.puissance + gain_puissance,
        instance.template.degats + gain_degats,
        gain_vie,
    )


def _score_duo(duo, role, tour, tours_max, pv_soi, pv_adv, conditions_forcees=False):
    puissance = degats = vie = 0.0
    for i, instance in enumerate(duo):
        # Le coequipier est connu : `puissance_alliee` est donc evaluable des le choix.
        allie = duo[1 - i] if len(duo) == 2 else None
        p, d, v = _score_combattant(
            instance, role, tour, tours_max, pv_soi, pv_adv,
            allie.template.puissance if allie else None, conditions_forcees,
        )
        puissance += p
        degats += d
        vie += v
    return puissance, degats, vie


def estimer_puissance_duo_adverse(joueur_adverse, instances_revelees):
    """Puissance totale probable du duo adverse, connaissant `instances_revelees` (0, 1 ou
    2 des Combattants qu'il engage). Les Combattants non reveles sont estimes a la
    Puissance moyenne de ceux qu'il peut encore engager."""
    connue = sum(inst.template.puissance for inst in instances_revelees)
    manquants = 2 - len(instances_revelees)
    if manquants <= 0:
        return connue
    candidats = [
        c for c in joueur_adverse.combattants_disponibles() if c not in instances_revelees
    ]
    if not candidats:
        return connue
    moyenne = sum(c.template.puissance for c in candidats) / len(candidats)
    return connue + manquants * moyenne


def choisir_duo(
    joueur, role, tour, tours_max, pv_soi, pv_adv, batailles_restantes,
    puissance_adverse_estimee=None, conditions_forcees=False,
):
    """Choisit le duo a engager parmi les duos legaux du joueur (cf.
    Joueur.duos_legaux, qui exclut ceux rendant les batailles suivantes injouables).
    Retourne un tuple de 2 CombattantEnEquipe."""
    duos = joueur.duos_legaux(batailles_restantes)
    evalues = [
        (_score_duo(duo, role, tour, tours_max, pv_soi, pv_adv, conditions_forcees), duo)
        for duo in duos
    ]

    if puissance_adverse_estimee is None:
        meilleur = max(score for score, _ in evalues)
        return random.choice([duo for score, duo in evalues if score == meilleur])

    # Duo adverse (partiellement) connu : gagner au meilleur prix plutot qu'au maximum.
    gagnants = [(score, duo) for score, duo in evalues if score[0] > puissance_adverse_estimee]
    if gagnants:
        cible = min(score for score, _ in gagnants)
        candidats = [duo for score, duo in gagnants if score == cible]
    else:
        cible = min(score for score, _ in evalues)
        candidats = [duo for score, duo in evalues if score == cible]
    return random.choice(candidats)


def _menace(combattant_adverse, tour, tours_max):
    """Poids heuristique du Pouvoir d'un Combattant adverse deja engage : de combien il
    fait bouger la Puissance et les Degats de sa bataille."""
    pouvoir = combattant_adverse.pouvoir()
    if pouvoir is None:
        return 0.0
    camp = combattant_adverse.camp
    allies = [c for c in camp.combattants if c is not combattant_adverse]
    gain_puissance, gain_degats, gain_vie = estimer_gain(
        pouvoir, camp.role, combattant_adverse.n_utilisation, tour, tours_max,
        camp.joueur.pv, camp.adversaire.joueur.pv,
        allies[0].template.puissance if allies else None, camp.conditions_forcees,
    )
    if (gain_puissance, gain_degats, gain_vie) == (0, 0, 0) and pouvoir.get("condition") in CONDITIONS_INCERTAINES:
        # Pouvoir conditionne par l'issue de la bataille : non estimable, mais pas inoffensif.
        return 1.0
    return abs(gain_puissance) + abs(gain_degats) + abs(gain_vie)


def _copiable(combattant_adverse):
    """Le Pouvoir de ce Combattant peut-il reellement etre copie ? (memes limitations que
    l'effet copie_pouvoir dans powers.py)"""
    from .powers import _contient_copie_pouvoir, _est_differee

    pouvoir = combattant_adverse.pouvoir()
    if pouvoir is None or combattant_adverse.stoppe:
        return False
    return not _est_differee(pouvoir) and not _contient_copie_pouvoir(pouvoir)


def choisir_cible(source, candidats, tour, tours_max):
    """Designe, parmi les 2 Combattants du camp adverse, celui que visent les effets a
    cible unique du Pouvoir de `source`.

    La regle depend de l'effet dominant du Pouvoir :
    - Echange : viser le plus fort (Puissance + Degats), c'est ce qu'on recupere.
    - Copie pouvoir : viser le Pouvoir copiable le plus utile.
    - Stop pouvoir : viser le Pouvoir le plus menacant.
    - Malus de Puissance / Degats : viser le Combattant de plus forte Puissance.
    """
    types = {effet["type"] for effet in (source.pouvoir() or {}).get("effets", [])}

    if "echange" in types:
        return max(candidats, key=lambda c: (c.puissance + c.degats, c.puissance))
    if "copie_pouvoir" in types:
        copiables = [c for c in candidats if _copiable(c)]
        if copiables:
            return max(copiables, key=lambda c: _menace(c, tour, tours_max))
    if "stop_pouvoir" in types:
        return max(candidats, key=lambda c: (_menace(c, tour, tours_max), c.puissance))
    return max(candidats, key=lambda c: (c.puissance, c.degats))


def choisir_ciblages(camp, tour, tours_max):
    """Designe les cibles de tous les Combattants du camp dont le Pouvoir en requiert une.
    Retourne {id du Combattant: id de la cible}."""
    ciblages = {}
    for combattant in camp.combattants:
        if not pouvoir_requiert_cible(combattant.pouvoir()):
            continue
        cible = choisir_cible(combattant, camp.adversaire.combattants, tour, tours_max)
        ciblages[combattant.template.id] = cible.template.id
    return ciblages


def choisir_revelation(duo):
    """Reperage : lequel des 2 Combattants du duo montrer a l'adversaire.

    L'adversaire deduit la force du duo de ce qu'il voit (cf.
    `estimer_puissance_duo_adverse`) : montrer le Combattant de plus faible Puissance
    minimise son estimation, donc le prix qu'il paiera pour esperer gagner."""
    return min(duo, key=lambda inst: (inst.template.puissance, inst.template.degats))


def choisir_second_souffle(joueur):
    """Second souffle : a quel Combattant de son equipe le vainqueur rend une utilisation.

    Seul un Combattant ayant deja depense une utilisation en gagne reellement une ;
    parmi eux, celui qu'on a le plus interet a pouvoir rejouer est le plus fort.
    Retourne None si aucun Combattant n'a encore ete engage."""
    candidats = [c for c in joueur.equipe if c.utilisations > 0]
    if not candidats:
        return None
    return max(candidats, key=lambda inst: (inst.template.puissance, inst.template.degats))


__all__ = [
    "TYPES_CIBLE_UNIQUE",
    "choisir_ciblages",
    "choisir_cible",
    "choisir_duo",
    "choisir_revelation",
    "choisir_second_souffle",
    "estimer_gain",
    "estimer_puissance_duo_adverse",
]
