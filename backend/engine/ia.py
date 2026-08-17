"""Heuristique de choix de l'IA : quel Combattant engager pour la manche en cours.

Version "des par personnage" : il n'y a plus de Glyphe a associer, le seul choix est
celui du Combattant. Ce choix porte desormais un arbitrage a double tranchant, puisque
les des adverses inscrits sur la carte engagee sont donnes a l'adversaire. L'IA evalue
donc une *marge* (sa Puissance estimee moins celle de l'adversaire) plutot que sa seule
Puissance, et estime les deux Pouvoirs en presence plutot que le sien seul :

- Puissance : esperance du pool de des de chaque camp (ses des personnels + les des
  adverses recus). L'esperance est exacte, la Puissance etant une simple somme.
- Energie : la distribution exacte du total d'Energie du pool est calculee par
  convolution des distributions de chaque de. On en tire la probabilite d'atteindre le
  seuil `energie_min` du Pouvoir, et l'Energie moyenne *sachant* que ce seuil est
  atteint (utilisee par le modificateur `par_energie`). Chaque effet est ensuite pondere
  par cette probabilite d'activation.
- Courage / Riposte / Vengeance / Domination sont verifiables immediatement (role du
  duel, PV courants). Victoire / Defaite / Surpuissance / Contrecoup dependent de
  l'issue du duel, inconnue au moment du choix : elles ne sont jamais comptees.
- Echange est estime exactement en esperance (les deux pools sont connus) : il vaut
  l'ecart de Puissance entre les deux camps, et l'ecart de Degats.
- Stop pouvoir, Protection et Copie pouvoir agissent sur l'estimation du Pouvoir d'en
  face : un Stop probable rabote le gain adverse, une Protection annule la part du gain
  adverse qui vise ce cote-ci, une Copie ajoute a son propre compte le gain immediat de
  l'adversaire.

Quand l'IA joue en second, elle connait le Combattant adverse, donc les deux pools
exacts. Quand elle joue en premier, elle moyenne son evaluation sur les Combattants
encore disponibles en face (les equipes sont visibles des deux cotes) ; elle ne cherche
pas a anticiper que l'adversaire choisira ensuite le meilleur contre.

Les egalites de score sont tranchees au hasard, pour eviter un jeu totalement previsible.
"""
import random
from functools import lru_cache

from .des import FACES_PAR_DE


@lru_cache(maxsize=None)
def _esperance_puissance(pool):
    """Esperance de la Puissance totale d'un pool de des (tuple de types de des)."""
    total = 0.0
    for type_de in pool:
        faces = FACES_PAR_DE[type_de]
        total += sum(p for p, _ in faces) / len(faces)
    return total


@lru_cache(maxsize=None)
def _distribution_energie(pool):
    """Distribution exacte du total d'Energie d'un pool, sous forme {total: probabilite}."""
    distribution = {0: 1.0}
    for type_de in pool:
        faces = FACES_PAR_DE[type_de]
        suivante = {}
        for total, proba in distribution.items():
            for _, energie in faces:
                suivante[total + energie] = suivante.get(total + energie, 0.0) + proba / len(faces)
        distribution = suivante
    return distribution


@lru_cache(maxsize=None)
def _esperance_energie(pool):
    return sum(total * proba for total, proba in _distribution_energie(pool).items())


@lru_cache(maxsize=None)
def _proba_et_energie_moyenne(pool, seuil):
    """(probabilite d'atteindre `seuil` d'Energie, Energie moyenne sachant ce seuil
    atteint) pour un pool donne."""
    distribution = _distribution_energie(pool)
    proba = sum(p for total, p in distribution.items() if total >= seuil)
    if proba <= 0:
        return 0.0, 0.0
    moyenne = sum(total * p for total, p in distribution.items() if total >= seuil) / proba
    return proba, moyenne


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


_ESTIMATION_NULLE = {
    "proba": 0.0, "puissance_soi": 0.0, "puissance_adv": 0.0, "degats_soi": 0.0,
    "vie": 0.0, "stop": False, "protection": False, "copie": False,
}


def _estimer_pouvoir(pouvoir, contexte):
    """Estime l'apport d'un Pouvoir, du point de vue du Combattant qui le possede.

    Retourne un dict :
    - `proba` : probabilite que l'Energie tiree atteigne le seuil d'activation ;
    - `puissance_soi` / `degats_soi` : bonus qu'il s'applique a lui-meme ;
    - `puissance_adv` : modification qu'il applique a la Puissance d'en face ;
    - `vie` : ecart de PV net en sa faveur ;
    - `stop` / `protection` / `copie` : presence des effets correspondants, exploites en
      croisant les deux estimations d'un meme duel.

    Les valeurs sont brutes (non ponderees par `proba`), la ponderation etant appliquee
    par l'appelant, qui doit aussi arbitrer les neutralisations croisees.
    """
    if pouvoir is None:
        return _ESTIMATION_NULLE
    if _condition_certaine(
        pouvoir.get("condition"), contexte["role"], contexte["pv_soi"], contexte["pv_adv"]
    ) is not True:
        return _ESTIMATION_NULLE

    modificateur = pouvoir.get("modificateur")
    if modificateur == "contrecoup":
        return _ESTIMATION_NULLE  # ne se declenche qu'en cas de victoire, inconnue au moment du choix

    proba, energie_moyenne = _proba_et_energie_moyenne(
        contexte["pool_soi"], pouvoir.get("energie_min", 0)
    )
    if proba <= 0:
        return _ESTIMATION_NULLE
    energie_adverse = _esperance_energie(contexte["pool_adv"])

    def valeur_effective(valeur):
        if modificateur == "par_energie":
            return valeur * energie_moyenne
        if modificateur == "par_energie_adverse":
            return valeur * energie_adverse
        if modificateur == "par_energie_en_jeu":
            return valeur * (energie_moyenne + energie_adverse)
        if modificateur == "patience":
            return valeur * contexte["duel_numero"]
        if modificateur == "impatience":
            return valeur * (contexte["duels_max"] - contexte["duel_numero"] + 1)
        return valeur

    estimation = dict(_ESTIMATION_NULLE, proba=proba)
    for effet in pouvoir.get("effets", []):
        type_effet = effet["type"]
        cible_soi = effet.get("cible", "soi") == "soi"
        if type_effet == "puissance":
            valeur = valeur_effective(effet.get("valeur", 0))
            estimation["puissance_soi" if cible_soi else "puissance_adv"] += valeur
        elif type_effet == "degats" and cible_soi:
            estimation["degats_soi"] += valeur_effective(effet.get("valeur", 0))
        elif type_effet == "vie":
            valeur = valeur_effective(effet.get("valeur", 0))
            estimation["vie"] += valeur if cible_soi else -valeur
        elif type_effet == "vampirisme":
            x = valeur_effective(effet.get("valeur", 0))
            estimation["vie"] += 2 * x  # -x cote adverse, +x cote soi : ecart net de 2x
        elif type_effet == "echange":
            # Les deux pools sont connus : l'echange vaut exactement l'ecart d'esperance.
            ecart_puissance = _esperance_puissance(contexte["pool_adv"]) - _esperance_puissance(contexte["pool_soi"])
            estimation["puissance_soi"] += ecart_puissance
            estimation["puissance_adv"] -= ecart_puissance
            estimation["degats_soi"] += contexte["degats_adv"] - contexte["degats_soi"]
        elif type_effet == "stop_pouvoir":
            estimation["stop"] = True
        elif type_effet == "protection":
            estimation["protection"] = True
        elif type_effet == "copie_pouvoir":
            estimation["copie"] = True
    return estimation


def _evaluer_paire(template_soi, template_adverse, role, duel_numero, duels_max, pv_soi, pv_adv):
    """Score (marge de Puissance, Degats estimes, ecart de Vie) du duel opposant
    `template_soi` a `template_adverse`, tous deux connus."""
    pool_soi = tuple(template_soi.des_personnels) + tuple(template_adverse.des_adverses)
    pool_adv = tuple(template_adverse.des_personnels) + tuple(template_soi.des_adverses)
    base_soi = {
        "pool_soi": pool_soi, "pool_adv": pool_adv,
        "degats_soi": template_soi.degats, "degats_adv": template_adverse.degats,
        "role": role, "pv_soi": pv_soi, "pv_adv": pv_adv,
        "duel_numero": duel_numero, "duels_max": duels_max,
    }
    base_adv = dict(
        base_soi,
        pool_soi=pool_adv, pool_adv=pool_soi,
        degats_soi=template_adverse.degats, degats_adv=template_soi.degats,
        role="j2" if role == "j1" else "j1", pv_soi=pv_adv, pv_adv=pv_soi,
    )
    est_soi = _estimer_pouvoir(template_soi.pouvoir, base_soi)
    est_adv = _estimer_pouvoir(template_adverse.pouvoir, base_adv)

    # Neutralisations croisees : un Stop pouvoir probable rabote tout le Pouvoir d'en
    # face, une Protection seulement la part de ce Pouvoir qui vise ce cote-ci.
    poids_soi = est_soi["proba"] * (1 - est_adv["proba"] if est_adv["stop"] else 1)
    poids_adv = est_adv["proba"] * (1 - est_soi["proba"] if est_soi["stop"] else 1)
    poids_soi_sur_adv = poids_soi * (1 - est_adv["proba"] if est_adv["protection"] else 1)
    poids_adv_sur_soi = poids_adv * (1 - est_soi["proba"] if est_soi["protection"] else 1)

    # Copie pouvoir : le copieur rejoue a son compte les effets immediats d'en face.
    copie_soi = poids_soi * poids_adv if est_soi["copie"] and not est_adv["copie"] else 0.0
    copie_adv = poids_adv * poids_soi if est_adv["copie"] and not est_soi["copie"] else 0.0

    puissance_soi = (
        _esperance_puissance(pool_soi)
        + poids_soi * est_soi["puissance_soi"]
        + poids_adv_sur_soi * est_adv["puissance_adv"]
        + copie_soi * est_adv["puissance_soi"]
    )
    puissance_adv = (
        _esperance_puissance(pool_adv)
        + poids_adv * est_adv["puissance_soi"]
        + poids_soi_sur_adv * est_soi["puissance_adv"]
        + copie_adv * est_soi["puissance_soi"]
    )
    degats = template_soi.degats + poids_soi * est_soi["degats_soi"] + copie_soi * est_adv["degats_soi"]
    vie = poids_soi * est_soi["vie"] - poids_adv * est_adv["vie"]
    return puissance_soi - puissance_adv, degats, vie


def choisir_combattant(joueur, adversaire, combattant_adverse, role, duel_numero, duels_max, pv_soi, pv_adv):
    """Choisit le Combattant a engager parmi ceux encore disponibles. Si le Combattant
    adverse est deja connu (l'IA joue en second), l'evaluation porte sur ce duel precis ;
    sinon elle est moyennee sur les Combattants encore disponibles en face."""
    if combattant_adverse is not None:
        templates_adverses = [combattant_adverse.template]
    else:
        templates_adverses = [c.template for c in adversaire.combattants_disponibles()]

    combinaisons = []
    for instance in joueur.combattants_disponibles():
        scores = [
            _evaluer_paire(instance.template, adverse, role, duel_numero, duels_max, pv_soi, pv_adv)
            for adverse in templates_adverses
        ]
        score = tuple(sum(valeurs) / len(scores) for valeurs in zip(*scores))
        combinaisons.append((score, instance))

    meilleur_score = max(score for score, _ in combinaisons)
    meilleures = [instance for score, instance in combinaisons if score == meilleur_score]
    return random.choice(meilleures)
