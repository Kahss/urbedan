"""Heuristique de l'IA : quel Combattant engager, puis quel de prendre dans le pool.

Version "draft de des". L'IA a deux decisions a prendre par duel, et le pool etant lance
avant le choix des Combattants, les deux se raisonnent sur une information complete
(a ceci pres que J1 ignore quel Combattant J2 engagera).

- **Choix du de** (`choisir_de`) : l'IA evalue, pour chaque de encore disponible, le gain
  marginal qu'il apporte a sa propre marge de Puissance, augmente d'une fraction du gain
  qu'il apporterait a l'adversaire (privation : prendre un de tres bon pour l'adversaire
  vaut mieux que prendre un de legerement meilleur pour soi). L'Energie n'est pas
  aleatoire ici : le total est connu de, donc l'activation du Pouvoir et son eventuel
  scaling `par_energie` sont calcules exactement.
- **Choix du Combattant** (`choisir_combattant`) : pour chaque Combattant disponible,
  l'IA *simule* le draft qui suivrait (meme heuristique des deux cotes, ordre donne par
  les initiatives) sur le pool reellement tire, puis note le duel obtenu. C'est ce qui
  permet de valoriser correctement l'initiative : un Combattant rapide securise les des
  dont son Pouvoir a besoin.

Comme dans les versions precedentes :
- Courage / Riposte / Vengeance / Domination sont evalues immediatement (role du duel,
  PV courants) ; Victoire / Defaite / Surpuissance / Contrecoup dependent de l'issue du
  duel et ne sont jamais comptes.
- Echange est estime exactement (les deux mains sont connues) : il vaut l'ecart de
  Puissance, et l'ecart de Degats.
- Stop pouvoir, Protection et Copie pouvoir sont croises entre les deux estimations d'un
  meme duel.

Les egalites de score sont tranchees au hasard lors des vraies decisions, et de facon
deterministe dans les simulations de draft (pour que l'evaluation d'un Combattant ne
depende pas du hasard).
"""
import random

# Poids relatifs dans le score scalaire : la marge de Puissance decide du duel, les
# Degats et la Vie n'en sont que la consequence.
POIDS_DEGATS = 0.5
POIDS_VIE = 0.5

# Part du gain adverse prise en compte quand l'IA drafte : prendre un de excellent pour
# l'adversaire a de la valeur meme s'il ne sert pas directement.
FACTEUR_PRIVATION = 0.5


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
    "actif": False, "puissance_soi": 0.0, "puissance_adv": 0.0, "degats_soi": 0.0,
    "vie": 0.0, "stop": False, "protection": False, "copie": False,
}


def _estimer_pouvoir(pouvoir, contexte):
    """Estime l'apport d'un Pouvoir, du point de vue du Combattant qui le possede.

    `actif` est booleen (et non probabiliste) : l'Energie des des draftes est connue au
    moment ou l'IA decide. Les autres champs sont les modifications apportees a soi
    (`puissance_soi`, `degats_soi`), a l'adversaire (`puissance_adv`), et l'ecart de PV
    net en sa faveur (`vie`). `stop` / `protection` / `copie` sont exploites par
    l'appelant, qui croise les deux estimations d'un meme duel.
    """
    if pouvoir is None:
        return _ESTIMATION_NULLE
    if contexte["energie_soi"] < pouvoir.get("energie_min", 0):
        return _ESTIMATION_NULLE
    if _condition_certaine(
        pouvoir.get("condition"), contexte["role"], contexte["pv_soi"], contexte["pv_adv"]
    ) is not True:
        return _ESTIMATION_NULLE

    modificateur = pouvoir.get("modificateur")
    if modificateur == "contrecoup":
        return _ESTIMATION_NULLE  # ne se declenche qu'en cas de victoire, inconnue au moment du choix

    def valeur_effective(valeur):
        if modificateur == "par_energie":
            return valeur * contexte["energie_soi"]
        if modificateur == "par_energie_adverse":
            return valeur * contexte["energie_adv"]
        if modificateur == "par_energie_en_jeu":
            return valeur * (contexte["energie_soi"] + contexte["energie_adv"])
        if modificateur == "patience":
            return valeur * contexte["duel_numero"]
        if modificateur == "impatience":
            return valeur * (contexte["duels_max"] - contexte["duel_numero"] + 1)
        return valeur

    estimation = dict(_ESTIMATION_NULLE, actif=True)
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
            ecart = contexte["puissance_adv"] - contexte["puissance_soi"]
            estimation["puissance_soi"] += ecart
            estimation["puissance_adv"] -= ecart
            estimation["degats_soi"] += contexte["degats_adv"] - contexte["degats_soi"]
        elif type_effet == "stop_pouvoir":
            estimation["stop"] = True
        elif type_effet == "protection":
            estimation["protection"] = True
        elif type_effet == "copie_pouvoir":
            estimation["copie"] = True
    return estimation


def _score(template_soi, des_soi, template_adv, des_adv, role, duel_numero, duels_max, pv_soi, pv_adv):
    """Score scalaire du duel, du point de vue de `template_soi` avec la main `des_soi` :
    marge de Puissance, plus une fraction des Degats et de l'ecart de Vie attendus."""
    puissance_soi = sum(de["puissance"] for de in des_soi)
    puissance_adv = sum(de["puissance"] for de in des_adv)
    energie_soi = sum(de["energie"] for de in des_soi)
    energie_adv = sum(de["energie"] for de in des_adv)
    role_adv = "j2" if role == "j1" else "j1"

    contexte_soi = {
        "puissance_soi": puissance_soi, "puissance_adv": puissance_adv,
        "energie_soi": energie_soi, "energie_adv": energie_adv,
        "degats_soi": template_soi.degats, "degats_adv": template_adv.degats,
        "role": role, "pv_soi": pv_soi, "pv_adv": pv_adv,
        "duel_numero": duel_numero, "duels_max": duels_max,
    }
    contexte_adv = dict(
        contexte_soi,
        puissance_soi=puissance_adv, puissance_adv=puissance_soi,
        energie_soi=energie_adv, energie_adv=energie_soi,
        degats_soi=template_adv.degats, degats_adv=template_soi.degats,
        role=role_adv, pv_soi=pv_adv, pv_adv=pv_soi,
    )
    est_soi = _estimer_pouvoir(template_soi.pouvoir, contexte_soi)
    est_adv = _estimer_pouvoir(template_adv.pouvoir, contexte_adv)

    # Neutralisations croisees : un Stop pouvoir annule tout le Pouvoir d'en face, une
    # Protection seulement la part de ce Pouvoir qui vise ce cote-ci.
    poids_soi = 0.0 if (est_adv["stop"] and est_adv["actif"]) else float(est_soi["actif"])
    poids_adv = 0.0 if (est_soi["stop"] and est_soi["actif"]) else float(est_adv["actif"])
    poids_soi_sur_adv = 0.0 if est_adv["protection"] and est_adv["actif"] else poids_soi
    poids_adv_sur_soi = 0.0 if est_soi["protection"] and est_soi["actif"] else poids_adv

    # Copie pouvoir : le copieur rejoue a son compte les effets immediats d'en face.
    copie_soi = poids_soi * poids_adv if est_soi["copie"] and not est_adv["copie"] else 0.0
    copie_adv = poids_adv * poids_soi if est_adv["copie"] and not est_soi["copie"] else 0.0

    totale_soi = (
        puissance_soi
        + poids_soi * est_soi["puissance_soi"]
        + poids_adv_sur_soi * est_adv["puissance_adv"]
        + copie_soi * est_adv["puissance_soi"]
    )
    totale_adv = (
        puissance_adv
        + poids_adv * est_adv["puissance_soi"]
        + poids_soi_sur_adv * est_soi["puissance_adv"]
        + copie_adv * est_soi["puissance_soi"]
    )
    degats = template_soi.degats + poids_soi * est_soi["degats_soi"] + copie_soi * est_adv["degats_soi"]
    vie = poids_soi * est_soi["vie"] - poids_adv * est_adv["vie"]
    return (totale_soi - totale_adv) + POIDS_DEGATS * degats + POIDS_VIE * vie


def choisir_de(template_soi, des_soi, template_adv, des_adv, pool, role,
               duel_numero, duels_max, pv_soi, pv_adv, aleatoire=True):
    """Choisit le de a prendre dans `pool` : celui qui maximise le gain marginal pour soi,
    augmente de `FACTEUR_PRIVATION` fois le gain qu'il aurait apporte a l'adversaire."""
    role_adv = "j2" if role == "j1" else "j1"
    commun = (duel_numero, duels_max)
    base_soi = _score(template_soi, des_soi, template_adv, des_adv, role, *commun, pv_soi, pv_adv)
    base_adv = _score(template_adv, des_adv, template_soi, des_soi, role_adv, *commun, pv_adv, pv_soi)

    meilleurs, meilleur_score = [], None
    for de in pool:
        gain_soi = _score(
            template_soi, des_soi + [de], template_adv, des_adv, role, *commun, pv_soi, pv_adv
        ) - base_soi
        gain_adv = _score(
            template_adv, des_adv + [de], template_soi, des_soi, role_adv, *commun, pv_adv, pv_soi
        ) - base_adv
        score = gain_soi + FACTEUR_PRIVATION * gain_adv
        if meilleur_score is None or score > meilleur_score + 1e-9:
            meilleurs, meilleur_score = [de], score
        elif score > meilleur_score - 1e-9:
            meilleurs.append(de)
    return random.choice(meilleurs) if aleatoire else meilleurs[0]


def _simuler_draft(template_j1, template_j2, pool, duel_numero, duels_max, pv_j1, pv_j2):
    """Rejoue le draft complet du pool avec la meme heuristique des deux cotes, dans
    l'ordre impose par les initiatives (J1 en cas d'egalite). Retourne (des J1, des J2).
    Deterministe : sert a evaluer un choix de Combattant, pas a jouer."""
    mains = {"j1": [], "j2": []}
    templates = {"j1": template_j1, "j2": template_j2}
    pv = {"j1": pv_j1, "j2": pv_j2}
    restants = list(pool)
    role = "j1" if template_j1.initiative >= template_j2.initiative else "j2"
    par_joueur = len(pool) // 2

    while restants and len(mains[role]) < par_joueur:
        adverse = "j2" if role == "j1" else "j1"
        de = choisir_de(
            templates[role], mains[role], templates[adverse], mains[adverse],
            restants, role, duel_numero, duels_max, pv[role], pv[adverse], aleatoire=False,
        )
        restants.remove(de)
        mains[role].append(de)
        role = adverse
    return mains["j1"], mains["j2"]


def choisir_combattant(joueur, adversaire, combattant_adverse, role, pool,
                       duel_numero, duels_max, pv_soi, pv_adv):
    """Choisit le Combattant a engager parmi ceux encore disponibles, en simulant pour
    chacun le draft qui suivrait sur le pool deja tire. Si le Combattant adverse est
    connu (l'IA joue en second), l'evaluation porte sur ce duel precis ; sinon elle est
    moyennee sur les Combattants encore disponibles en face."""
    if combattant_adverse is not None:
        templates_adverses = [combattant_adverse.template]
    else:
        templates_adverses = [c.template for c in adversaire.combattants_disponibles()]

    meilleurs, meilleur_score = [], None
    for instance in joueur.combattants_disponibles():
        scores = []
        for template_adverse in templates_adverses:
            if role == "j1":
                des_soi, des_adv = _simuler_draft(
                    instance.template, template_adverse, pool, duel_numero, duels_max, pv_soi, pv_adv
                )
            else:
                des_adv, des_soi = _simuler_draft(
                    template_adverse, instance.template, pool, duel_numero, duels_max, pv_adv, pv_soi
                )
            scores.append(_score(
                instance.template, des_soi, template_adverse, des_adv,
                role, duel_numero, duels_max, pv_soi, pv_adv,
            ))
        moyenne = sum(scores) / len(scores) if scores else 0.0
        if meilleur_score is None or moyenne > meilleur_score + 1e-9:
            meilleurs, meilleur_score = [instance], moyenne
        elif moyenne > meilleur_score - 1e-9:
            meilleurs.append(instance)
    return random.choice(meilleurs)
