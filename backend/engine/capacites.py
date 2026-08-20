"""Resolution des Capacites (version Eredice).

Une Capacite est definie par :
- `cout` : 1 a 3 cases. Chaque case est une couleur ("rouge", "bleu", "jaune") ou
  `null` (joker : un De de n'importe quelle couleur).
- `condition` (optionnelle) : mot-cle qui doit etre verifie pour que la Capacite
  s'active.
- `multiplicateur` (optionnel) : mot-cle qui multiplie la valeur des effets.
- `effets` : liste d'effets appliques a l'activation.

Regles de resolution retenues pour ce POC (cf. README.md) :
- L'activation est OBLIGATOIRE : des qu'un De ajoute sur un Personnage permet de payer
  le cout d'une de ses Capacites (condition incluse), celle-ci s'active immediatement.
- Un Personnage teste ses Capacites dans leur ordre de declaration : la premiere
  payable s'active. On recommence ensuite le test (cascade) tant qu'une Capacite est
  payable, dans la limite de MAX_CASCADE activations par De ajoute.
- Seuls les Des payant le cout sont defausses ; le surplus reste stocke.
- Choix du paiement : parmi tous les paiements possibles, on retient d'abord ceux qui
  satisfont la condition (utile pour `monochrome` / `polychrome`), puis celui qui
  consomme les couleurs les plus abondantes de la reserve, puis les Des les plus
  anciens. Le paiement est donc deterministe (pas de choix demande au joueur).
- Les effets de manipulation de Des ciblent toujours automatiquement (aucune invite
  supplementaire) : `de_bonus` prend dans le pool la couleur la plus abondante,
  `de_vole` / `de_defausse` visent le Personnage adverse qui stocke le plus de Des
  (egalite : le plus avance dans la piste d'initiative) et lui prennent son De le plus
  ancien.
- Les modifications d'Attaque sont permanentes (le reste de la partie) et l'Attaque
  effective ne descend jamais sous 0.
- Les modifications d'Initiative sont des deplacements de PLACES dans la piste (les
  valeurs d'Initiative ne servent qu'au placement initial) : la piste est modifiee
  immediatement, mais la sequence de draft du round en cours a ete figee a son debut,
  donc l'effet se ressent des le round suivant.
"""
import itertools
from collections import Counter

from .models import COULEURS, De, PV_DEPART

MAX_CASCADE = 12


# ------------------------------------------------------------------- paiement

def _candidats_paiement(perso, cout):
    """Tous les paiements possibles du `cout` avec les Des stockes du Personnage,
    classes par ordre de preference (couleurs les plus abondantes d'abord, puis Des
    les plus anciens)."""
    reserve = perso.des_stockes
    taille = len(cout)
    if taille == 0 or len(reserve) < taille:
        return []
    demandes = Counter(c for c in cout if c is not None)
    abondance = Counter(d.couleur for d in reserve)

    candidats = []
    for combo in itertools.combinations(range(len(reserve)), taille):
        des = [reserve[i] for i in combo]
        dispo = Counter(d.couleur for d in des)
        if any(dispo[couleur] < n for couleur, n in demandes.items()):
            continue
        # Les cases joker absorbent le reste : la taille du combo garantit la coherence.
        cle = (-sum(abondance[d.couleur] for d in des), combo)
        candidats.append((cle, des))
    candidats.sort(key=lambda c: c[0])
    return [des for _, des in candidats]


def trouver_paiement(perso, capacite, partie):
    """Retourne le paiement retenu (liste de Des) si la Capacite est activable, sinon
    None."""
    for paiement in _candidats_paiement(perso, capacite.get("cout", [])):
        if _condition_ok(capacite.get("condition"), perso, paiement, partie):
            return paiement
    return None


# ------------------------------------------------------------------ conditions

def _condition_ok(condition, perso, paiement, partie):
    if condition is None:
        return True
    joueur = perso.joueur
    adversaire = partie.adversaire(joueur)
    couleurs = [d.couleur for d in paiement]
    if condition == "vengeance":
        return adversaire.pv > joueur.pv
    if condition == "domination":
        return adversaire.pv < joueur.pv
    if condition == "blesse":
        return joueur.pv <= PV_DEPART // 2
    if condition == "monochrome":
        return len(set(couleurs)) == 1
    if condition == "polychrome":
        return len(set(couleurs)) == len(couleurs)
    if condition == "tete_de_piste":
        return partie.position_piste(perso) <= 1
    if condition == "queue_de_piste":
        return partie.position_piste(perso) >= len(partie.piste) - 2
    return True  # mot-cle inconnu : Capacite consideree comme non conditionnee


# --------------------------------------------------------------- multiplicateur

def _multiplicateur(capacite, perso, paiement, partie):
    mod = capacite.get("multiplicateur")
    if mod is None:
        return 1
    if mod == "par_de":
        return len(paiement)
    if mod == "patience":
        return partie.round_numero
    if mod == "par_perso_charge":
        # Compte avant defausse du paiement (le Personnage qui active compte donc).
        return sum(1 for p in perso.joueur.equipe if p.des_stockes)
    return 1


# -------------------------------------------------------------------- effets

def _cible_adverse_chargee(perso, partie):
    """Le Personnage adverse stockant le plus de Des (egalite : le plus avance dans la
    piste d'initiative), ou None si aucun n'en stocke."""
    adversaire = partie.adversaire(perso.joueur)
    candidats = [p for p in adversaire.equipe if p.des_stockes]
    if not candidats:
        return None
    return min(candidats, key=lambda p: (-len(p.des_stockes), partie.position_piste(p)))


def _personnages_cibles(perso, cible, partie):
    if cible == "equipe":
        return list(perso.joueur.equipe)
    if cible == "equipe_adverse":
        return list(partie.adversaire(perso.joueur).equipe)
    return [perso]


def _appliquer_effet(partie, perso, effet, mult):
    joueur = perso.joueur
    adversaire = partie.adversaire(joueur)
    type_effet = effet["type"]
    valeur = effet.get("valeur", 0) * mult
    nom = perso.template.nom

    if type_effet == "degats":
        partie.modifier_pv(adversaire, -valeur, f"Capacite de {nom}")

    elif type_effet == "soin":
        partie.modifier_pv(joueur, valeur, f"Capacite de {nom}")

    elif type_effet == "vampirisme":
        partie.modifier_pv(adversaire, -valeur, f"Vampirisme de {nom}")
        partie.modifier_pv(joueur, valeur, f"Vampirisme de {nom}")

    elif type_effet == "attaque":
        cibles = _personnages_cibles(perso, effet.get("cible", "soi"), partie)
        for cible in cibles:
            cible.bonus_attaque += valeur
        libelle = ", ".join(f"{c.template.nom} (Attaque {c.attaque})" for c in cibles)
        signe = "+" if valeur >= 0 else ""
        partie.log(f"{nom} : {signe}{valeur} Attaque -> {libelle}")

    elif type_effet == "initiative":
        avant = partie.position_piste(perso)
        apres = partie.deplacer_piste(perso, valeur)
        if apres == avant:
            partie.log(f"{nom} : deplacement d'initiative impossible (deja en position {avant + 1})")
        else:
            partie.log(
                f"{nom} : passe de la position {avant + 1} a la position {apres + 1} "
                "de la piste d'initiative (effectif des le round suivant)"
            )

    elif type_effet == "de_bonus":
        de = partie.retirer_du_pool_meilleure_couleur()
        if de is None:
            partie.log(f"{nom} : aucun De disponible dans le pool")
        else:
            perso.des_stockes.append(de)
            partie.log(f"{nom} drafte un De bonus ({de.couleur}) depuis le pool")

    elif type_effet == "de_cree":
        couleur = effet.get("couleur") or COULEURS[0]
        de = De(couleur)
        perso.des_stockes.append(de)
        partie.log(f"{nom} cree un De {couleur} et le stocke")

    elif type_effet == "de_vole":
        victime = _cible_adverse_chargee(perso, partie)
        if victime is None:
            partie.log(f"{nom} : aucun De stocke a voler chez l'adversaire")
        else:
            de = victime.des_stockes.pop(0)
            perso.des_stockes.append(de)
            partie.log(f"{nom} vole un De {de.couleur} a {victime.template.nom}")

    elif type_effet == "de_defausse":
        victime = _cible_adverse_chargee(perso, partie)
        if victime is None:
            partie.log(f"{nom} : aucun De stocke a defausser chez l'adversaire")
        else:
            de = victime.des_stockes.pop(0)
            partie.log(f"{nom} defausse un De {de.couleur} de {victime.template.nom}")

    elif type_effet == "relance_pool":
        nombre = partie.relancer_pool()
        partie.log(f"{nom} relance les {nombre} De(s) restant(s) du pool")

    else:
        partie.log(f"{nom} : effet inconnu '{type_effet}', ignore")


# ------------------------------------------------------------------ activation

def _activer(partie, perso, capacite, paiement):
    mult = _multiplicateur(capacite, perso, paiement, partie)
    for de in paiement:
        perso.des_stockes.remove(de)
    perso.activations += 1
    couleurs = "+".join(d.couleur for d in paiement)
    suffixe = f" (x{mult})" if mult != 1 else ""
    partie.log(
        f"CAPACITE {perso.template.nom} : {capacite.get('description', '')} "
        f"[paye {couleurs}]{suffixe}"
    )
    for effet in capacite.get("effets", []):
        if partie.terminee:
            return
        _appliquer_effet(partie, perso, effet, mult)


def resoudre_activations(partie, perso):
    """Active obligatoirement, en cascade, toutes les Capacites payables du Personnage.

    Appele apres chaque ajout de De sur ce Personnage. La cascade est bornee par
    MAX_CASCADE pour se proteger d'une boucle (une Capacite qui se re-alimente elle
    meme via `de_bonus` / `de_cree` / `de_vole`)."""
    for _ in range(MAX_CASCADE):
        if partie.terminee:
            return
        for capacite in perso.template.capacites:
            paiement = trouver_paiement(perso, capacite, partie)
            if paiement is not None:
                _activer(partie, perso, capacite, paiement)
                break
        else:
            return
    partie.log(
        f"{perso.template.nom} : limite de {MAX_CASCADE} activations en cascade atteinte"
    )


def capacites_activables(perso, partie):
    """Indices des Capacites du Personnage actuellement payables (pour l'IA et
    l'affichage)."""
    return [
        i for i, capacite in enumerate(perso.template.capacites)
        if trouver_paiement(perso, capacite, partie) is not None
    ]
