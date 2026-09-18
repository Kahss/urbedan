"""Analyse des matchups entre chaque paire de Combattants d'Urban Eredan.

Deux mesures complementaires, calculees separement :

1. Duels isoles controles (une paire de Combattants, toutes choses egales par
   ailleurs) : pour chaque paire {A, B}, on rejoue un grand nombre de duels 1
   contre 1 (pioche "stop ou encore" reelle, resolution des Pouvoirs reelle),
   en randomisant le contexte qui echapperait sinon a l'analyse (role J1/J2,
   numero du duel, PV de chacun, victoire/defaite au duel precedent). On en
   deduit le % de victoire de A face a B independamment de toute equipe : la
   matrice de matchups. L'ecart-type de cette matrice pour un personnage
   donne (parmi tous ses adversaires) mesure a quel point son identite est
   "rock-paper-scissors" (fort contre certains, faible contre d'autres).

2. Taux de victoire d'equipe (parties 4v4 completes, cf. generate_metagame.py) :
   pour chaque personnage, le % de victoire de l'equipe dont il fait partie,
   sur des parties simulees integralement par l'IA existante (engine/ia.py).
   L'ecart-type de ce taux entre personnages mesure l'equilibre global du
   roster.

L'objectif de design recherche (cf. discussion) : un ecart-type ELEVE cote (1)
- matchups riches et contrastes duo a duo - mais FAIBLE cote (2) - aucun
personnage nettement au-dessus ou en-dessous des autres une fois les parties
completes jouees.

Usage :
    python analyse_matchups.py [--n-duels 2000] [--n-parties 20000]
                                [--sans-graphique] [--sortie-dir out]
"""
import argparse
import itertools
import os
import random
import statistics
import sys

from _bootstrap import BASE_DIR, DATA_PATH, ecrire_csv, progression  # noqa: E402

from engine.game import (  # noqa: E402
    NB_DUELS_MAX,
    Partie,
    charger_combattants,
    tirer_equipe_equilibree,
)
from engine.ia import choisir_combattant, decider_piocher_ou_arreter  # noqa: E402
from engine.models import CombattantEnEquipe, Joueur, construire_deck_cartes_puissance  # noqa: E402
from engine.powers import a_effet, malus_effectif, resoudre_duel  # noqa: E402

N_DUELS_DEFAUT = 2000
N_PARTIES_DEFAUT = 20000
PV_MAX_ALEATOIRE = 15  # borne haute arbitraire pour randomiser vengeance/domination


# --------------------------------------------------------------- duels isoles
def _jouer_pioche_duel(template_j1, template_j2):
    """Rejoue la phase de pioche "stop ou encore" pour un duel isole entre deux
    Combattants (meme logique d'alternance et de pioche forcee que
    Partie._demarrer_pioche/_appliquer_decision_pioche, sans les mecanismes
    purement informationnels comme le masquage de cartes qui n'affectent pas la
    resolution)."""
    deck = construire_deck_cartes_puissance()
    cartes = {"j1": [], "j2": []}
    arrete = {"j1": False, "j2": False}
    templates = {"j1": template_j1, "j2": template_j2}
    tour = "j1"

    while not (arrete["j1"] and arrete["j2"]):
        template = templates[tour]
        mes_cartes = cartes[tour]

        if len(mes_cartes) == 0 and a_effet(template, "double_pioche_premiere") and len(deck) >= 2:
            carte_a, carte_b = deck.pop(), deck.pop()
            if (carte_a.puissance, -carte_a.malus) >= (carte_b.puissance, -carte_b.malus):
                gardee, remise = carte_a, carte_b
            else:
                gardee, remise = carte_b, carte_a
            mes_cartes.append(gardee)
            deck.append(remise)
        elif deck:
            malus_courant = malus_effectif(mes_cartes, template)
            action = decider_piocher_ou_arreter(mes_cartes, malus_courant, list(deck), template.malus_limite)
            if action == "piocher":
                mes_cartes.append(deck.pop())
            else:
                arrete[tour] = True
        else:
            arrete[tour] = True

        if not arrete[tour] and malus_effectif(mes_cartes, template) >= template.malus_limite:
            arrete[tour] = True

        autre = "j2" if tour == "j1" else "j1"
        if not arrete[autre]:
            tour = autre

    return cartes["j1"], cartes["j2"]


def _contexte_precedent_aleatoire(duel_numero):
    """Tire au hasard un contexte de duel precedent plausible (aucun au duel 1,
    sinon l'un des deux camps a gagne le duel d'avant), pour que les Pouvoirs
    conditionnes par Victoire/Defaite precedente (cf. powers.py) soient testes
    des deux cotes en moyenne plutot que toujours a False."""
    if duel_numero == 1:
        return False, False, False, False
    if random.random() < 0.5:
        return True, False, False, True  # j1 a gagne le duel precedent
    return False, True, True, False  # j2 a gagne le duel precedent


def simuler_duel_isole(template_a, template_b):
    """Simule un duel isole entre deux Combattants, contexte randomise (role
    J1/J2, numero de duel, PV de chacun, issue du duel precedent) pour ne pas
    figer artificiellement les Pouvoirs qui en dependent. Retourne 'a', 'b' ou
    'double' (egalite de Puissance -> double victoire)."""
    a_est_j1 = random.random() < 0.5
    template_j1, template_j2 = (template_a, template_b) if a_est_j1 else (template_b, template_a)

    cartes_j1, cartes_j2 = _jouer_pioche_duel(template_j1, template_j2)

    duel_numero = random.randint(1, NB_DUELS_MAX)
    victoire_prec_j1, defaite_prec_j1, victoire_prec_j2, defaite_prec_j2 = _contexte_precedent_aleatoire(duel_numero)

    joueur_j1 = Joueur("j1", False, [])
    joueur_j2 = Joueur("j2", False, [])
    joueur_j1.pv = random.randint(1, PV_MAX_ALEATOIRE)
    joueur_j2.pv = random.randint(1, PV_MAX_ALEATOIRE)

    resultat = resoudre_duel(
        joueur_j1, CombattantEnEquipe(template_j1), cartes_j1,
        joueur_j2, CombattantEnEquipe(template_j2), cartes_j2,
        duel_numero, NB_DUELS_MAX,
        victoire_prec_j1, defaite_prec_j1, victoire_prec_j2, defaite_prec_j2,
    )

    gagnants_ids = set(resultat["gagnants_ids"])
    a_gagne = template_a.id in gagnants_ids
    b_gagne = template_b.id in gagnants_ids
    if a_gagne and b_gagne:
        return "double"
    return "a" if a_gagne else "b"


def calculer_matrice_matchups(templates, ids, n_duels):
    """Renvoie matrice[a][b] = % de victoire de a face a b (matrice[a][a] = None).
    Chaque paire n'est simulee qu'une fois (les deux sens s'en deduisent : la
    somme des deux taux vaut toujours 100%)."""
    matrice = {a: {b: None for b in ids} for a in ids}
    total_paires = len(ids) * (len(ids) - 1) // 2
    fait = 0

    for a, b in itertools.combinations(ids, 2):
        victoires_a = 0.0
        victoires_b = 0.0
        for _ in range(n_duels):
            issue = simuler_duel_isole(templates[a], templates[b])
            if issue == "a":
                victoires_a += 1
            elif issue == "b":
                victoires_b += 1
            else:
                victoires_a += 0.5
                victoires_b += 0.5
        taux_a = 100 * victoires_a / n_duels
        matrice[a][b] = taux_a
        matrice[b][a] = 100 - taux_a

        fait += 1
        progression(fait, total_paires, "duels isoles", divisions=20)

    return matrice


# ------------------------------------------------------------ parties 4v4
def _jouer_partie_ia_vs_ia(templates):
    """Joue une partie 4v4 complete, les deux camps pilotes par l'heuristique IA
    existante (engine/ia.py), comme generate_metagame.py / simulate_puissance.py."""
    equipe_a_ids = tirer_equipe_equilibree(templates)
    partie = Partie(templates, equipe_a_ids)

    def jouer_choix(role, joueur, adversaire):
        instance = choisir_combattant(joueur, role, partie.duel_numero, NB_DUELS_MAX, joueur.pv, adversaire.pv)
        partie.soumettre_combattant(instance.template.id)

    while not partie.terminee:
        if partie.phase == "choix_combattant":
            if partie.j1 is partie.joueur_humain and partie.combattant_j1 is None:
                jouer_choix("j1", partie.joueur_humain, partie.joueur_ia)
            elif partie.j2 is partie.joueur_humain and partie.combattant_j2 is None:
                jouer_choix("j2", partie.joueur_humain, partie.joueur_ia)
        elif partie.phase == "pioche":
            slot = "j1" if partie.j1 is partie.joueur_humain else "j2"
            cartes = partie.cartes_j1 if slot == "j1" else partie.cartes_j2
            action = decider_piocher_ou_arreter(cartes, sum(c.malus for c in cartes), list(partie.deck_cartes))
            partie.decider_pioche(action)
        elif partie.phase == "duel_resolu":
            partie.duel_suivant()

    equipe_b_ids = [c.template.id for c in partie.joueur_ia.equipe]
    return equipe_a_ids, equipe_b_ids, partie.vainqueur


def calculer_taux_victoire_equipe(templates, ids, n_parties):
    stats = {cid: {"parties": 0, "victoires": 0} for cid in ids}

    for i in range(n_parties):
        equipe_a, equipe_b, vainqueur = _jouer_partie_ia_vs_ia(templates)
        for cid in equipe_a:
            stats[cid]["parties"] += 1
            if vainqueur == "humain":
                stats[cid]["victoires"] += 1
            elif vainqueur is None:
                stats[cid]["victoires"] += 0.5
        for cid in equipe_b:
            stats[cid]["parties"] += 1
            if vainqueur == "ia":
                stats[cid]["victoires"] += 1
            elif vainqueur is None:
                stats[cid]["victoires"] += 0.5
        progression(i + 1, n_parties, "parties 4v4")

    return {
        cid: (100 * s["victoires"] / s["parties"] if s["parties"] else 0.0)
        for cid, s in stats.items()
    }


# --------------------------------------------------------------------- rapport
def ecrire_csv_matrice(chemin, templates, ids, matrice):
    ids_tries = sorted(ids, key=lambda cid: templates[cid].nom)
    header = [""] + [templates[cid].nom for cid in ids_tries]
    rows = [
        [templates[a].nom] + ["" if a == b else f"{matrice[a][b]:.1f}" for b in ids_tries]
        for a in ids_tries
    ]
    ecrire_csv(chemin, header, rows)


def ecrire_csv_resume(chemin, lignes_resume):
    header = [
        "combattant", "niveau", "moyenne_matchups_pct", "ecart_type_matchups_pct",
        "meilleur_matchup", "pire_matchup", "taux_victoire_equipe_pct",
    ]
    rows = [
        [r["nom"], r["niveau"], f"{r['moyenne']:.1f}", f"{r['ecart_type']:.1f}",
         r["meilleur"], r["pire"], f"{r['taux_equipe']:.1f}"]
        for r in lignes_resume
    ]
    ecrire_csv(chemin, header, rows)


SEGMENTS_BORNES = [0, 20, 40, 60, 80, 100]


def generer_heatmap(chemin, templates, ids, matrice, segments=False):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import BoundaryNorm

    ids_tries = sorted(ids, key=lambda cid: templates[cid].nom)
    noms = [templates[cid].nom for cid in ids_tries]
    n = len(ids_tries)
    donnees = [[50.0 if a == b else matrice[a][b] for b in ids_tries] for a in ids_tries]

    taille = max(8, n * 0.4)
    fig, ax = plt.subplots(figsize=(taille, taille))

    if segments:
        # 5 segments fixes de 20 points chacun (au lieu d'un degrade continu) : plus
        # facile a lire d'un coup d'oeil, au prix de la precision entre deux duos.
        cmap = plt.get_cmap("RdYlGn", len(SEGMENTS_BORNES) - 1)
        norm = BoundaryNorm(SEGMENTS_BORNES, cmap.N)
        im = ax.imshow(donnees, cmap=cmap, norm=norm)
    else:
        im = ax.imshow(donnees, cmap="RdYlGn", vmin=0, vmax=100)

    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(noms, rotation=90, fontsize=7)
    ax.set_yticklabels(noms, fontsize=7)
    ax.set_xlabel("Adversaire")
    ax.set_ylabel("Combattant (% de victoire face a l'adversaire)")
    ax.set_title("Matrice des matchups 1v1 (duels isoles)")

    cbar = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02, ticks=SEGMENTS_BORNES if segments else None)
    cbar.set_label("% de victoire")
    if segments:
        cbar.set_ticklabels([f"{b}%" for b in SEGMENTS_BORNES])

    fig.tight_layout()
    fig.savefig(chemin, dpi=150)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(
        description="Analyse les matchups 1v1 entre chaque paire de Combattants et le "
        "taux de victoire d'equipe (parties 4v4), pour etudier l'equilibre du roster."
    )
    parser.add_argument("--n-duels", type=int, default=N_DUELS_DEFAUT,
                         help=f"Duels isoles simules par paire (defaut : {N_DUELS_DEFAUT})")
    parser.add_argument("--n-parties", type=int, default=N_PARTIES_DEFAUT,
                         help=f"Parties 4v4 simulees pour le taux de victoire d'equipe (defaut : {N_PARTIES_DEFAUT})")
    parser.add_argument("--sortie-dir", default=BASE_DIR,
                         help="Dossier de sortie pour les CSV et le graphique (defaut : racine du projet)")
    parser.add_argument("--sans-graphique", action="store_true",
                         help="Ne pas generer la heatmap PNG (evite la dependance matplotlib)")
    parser.add_argument("--heatmap-segments", action="store_true",
                         help="Heatmap en 5 segments de 20%% (0-20/20-40/.../80-100) au lieu d'un "
                              "degrade continu, pour une lecture plus rapide")
    args = parser.parse_args()

    templates = charger_combattants(DATA_PATH)
    ids = list(templates.keys())

    print(f"Chargement de {len(ids)} Combattants depuis {DATA_PATH}", file=sys.stderr)
    print(f"Etape 1/2 : duels isoles ({args.n_duels}/paire, {len(ids) * (len(ids) - 1) // 2} paires)", file=sys.stderr)
    matrice = calculer_matrice_matchups(templates, ids, args.n_duels)

    print(f"Etape 2/2 : parties 4v4 ({args.n_parties} parties)", file=sys.stderr)
    taux_equipe = calculer_taux_victoire_equipe(templates, ids, args.n_parties)

    lignes_resume = []
    for cid in ids:
        taux_face_aux_autres = [matrice[cid][autre] for autre in ids if autre != cid]
        moyenne = statistics.mean(taux_face_aux_autres)
        ecart_type = statistics.pstdev(taux_face_aux_autres)
        meilleur_id = max((autre for autre in ids if autre != cid), key=lambda o: matrice[cid][o])
        pire_id = min((autre for autre in ids if autre != cid), key=lambda o: matrice[cid][o])
        lignes_resume.append({
            "id": cid,
            "nom": templates[cid].nom,
            "niveau": templates[cid].niveau,
            "moyenne": moyenne,
            "ecart_type": ecart_type,
            "meilleur": f"{templates[meilleur_id].nom} ({matrice[cid][meilleur_id]:.0f}%)",
            "pire": f"{templates[pire_id].nom} ({matrice[cid][pire_id]:.0f}%)",
            "taux_equipe": taux_equipe[cid],
        })

    os.makedirs(args.sortie_dir, exist_ok=True)
    chemin_matrice = os.path.join(args.sortie_dir, "matchups_matrice.csv")
    chemin_resume = os.path.join(args.sortie_dir, "matchups_resume.csv")
    ecrire_csv_matrice(chemin_matrice, templates, ids, matrice)
    ecrire_csv_resume(chemin_resume, lignes_resume)

    chemin_heatmap = None
    if not args.sans_graphique:
        chemin_heatmap = os.path.join(args.sortie_dir, "matchups_heatmap.png")
        generer_heatmap(chemin_heatmap, templates, ids, matrice, segments=args.heatmap_segments)

    # ------------------------------------------------------------- rapport console
    lignes_resume.sort(key=lambda r: r["ecart_type"], reverse=True)
    largeur_nom = max(len(r["nom"]) for r in lignes_resume)

    print(f"\nDuels isoles 1v1 ({args.n_duels} par paire) - tries par ecart-type de matchup decroissant\n")
    entete = (
        f"{'Combattant':<{largeur_nom}}  {'Niv':>3}  {'Moy. matchups':>13}  {'Ecart-type':>10}  "
        f"{'Meilleur matchup':>22}  {'Pire matchup':>22}  {'Taux equipe (4v4)':>18}"
    )
    print(entete)
    print("-" * len(entete))
    for r in lignes_resume:
        print(
            f"{r['nom']:<{largeur_nom}}  {r['niveau']:>3}  {r['moyenne']:>12.1f}%  {r['ecart_type']:>9.1f}%  "
            f"{r['meilleur']:>22}  {r['pire']:>22}  {r['taux_equipe']:>17.1f}%"
        )

    ecarts_types_matchups = [r["ecart_type"] for r in lignes_resume]
    taux_equipe_tous = [r["taux_equipe"] for r in lignes_resume]
    print("\nSynthese design (objectif : (1) eleve, (2) faible)\n")
    print(f"(1) Ecart-type moyen des matchups 1v1 par personnage : {statistics.mean(ecarts_types_matchups):.1f} points")
    print(f"(2) Ecart-type du taux de victoire d'equipe entre personnages : {statistics.pstdev(taux_equipe_tous):.1f} points")
    print(f"    (taux de victoire d'equipe : min {min(taux_equipe_tous):.1f}% / max {max(taux_equipe_tous):.1f}% / moyenne {statistics.mean(taux_equipe_tous):.1f}%)")

    print(f"\nMatrice complete : {chemin_matrice}")
    print(f"Resume par personnage : {chemin_resume}")
    if chemin_heatmap:
        print(f"Heatmap : {chemin_heatmap}")


if __name__ == "__main__":
    main()
