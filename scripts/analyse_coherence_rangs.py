"""Analyse la coherence des rangs (niveaux) des Combattants d'Urban Eredan.

Principe : pour un personnage cible de rang R, on le fait jouer dans des parties
ou tout le reste de la table (ses 3 coequipiers ET les 4 adversaires) est compose
de personnages d'un rang de reference Ref, choisi ainsi :

    - rang 1 -> reference rang 2 (un rang 1 doit affaiblir son equipe face a du rang 2)
    - rang 2 -> reference rang 3 (un rang 2 doit affaiblir son equipe face a du rang 3)
    - rang 3 -> reference rang 2 (un rang 3 doit renforcer son equipe face a du rang 2)

Equipe A (celle du personnage cible) = [cible] + 3 personnages de rang Ref tires au
hasard. Equipe B (adverse) = 4 autres personnages de rang Ref (disjoints de ceux de
l'equipe A). On mesure le taux de victoire de l'equipe A sur un grand nombre de
parties simulees par l'IA existante (engine/ia.py) des deux cotes.

Lecture attendue :
    - rang 1 et rang 2 : taux de victoire d'equipe A < 50% (le personnage cible,
      plus faible que son environnement de reference, tire son equipe vers le bas).
    - rang 3 : taux de victoire d'equipe A > 50% (le personnage cible, plus fort que
      son environnement de reference, tire son equipe vers le haut).

Ces compositions depassent volontairement NIVEAU_TOTAL_MAX (la limite de somme de
niveaux qui borne une equipe en jeu reel, cf. engine/game.py) : il s'agit d'une
analyse theorique de calibrage, pas d'une partie jouable normalement, donc cette
limite est deliberement ignoree (les equipes sont construites directement, sans
passer par le constructeur de Partie qui la verifie).

Usage :
    python analyse_coherence_rangs.py [--n-parties 2000] [--sortie-dir out]
"""
import argparse
import csv
import os
import random
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "backend"))

from engine.game import NB_DUELS_MAX, PV_DEPART, Partie, charger_combattants  # noqa: E402
from engine.ia import choisir_combattant, decider_piocher_ou_arreter  # noqa: E402
from engine.models import CombattantEnEquipe, Joueur  # noqa: E402

DATA_PATH = os.path.join(PROJECT_ROOT, "data", "combattants.json")

N_PARTIES_DEFAUT = 2000

# Rang de reference dans lequel plonger un personnage du rang cle, pour tester sa
# coherence (cf. docstring du module).
RANG_REFERENCE = {1: 2, 2: 3, 3: 2}
DIRECTION_ATTENDUE = {1: "< 50%", 2: "< 50%", 3: "> 50%"}


def construire_partie_libre(templates_par_id, equipe_a_ids, equipe_b_ids):
    """Construit une Partie a partir de deux equipes explicites, en shortcutant le
    constructeur habituel (qui tire l'equipe adverse au hasard et refuse toute
    equipe dont la somme des niveaux depasse NIVEAU_TOTAL_MAX) : reproduit exactement
    le reste de l'initialisation de Partie.__init__ (cf. engine/game.py)."""
    partie = Partie.__new__(Partie)
    partie.joueur_humain = Joueur(
        "humain", False, [CombattantEnEquipe(templates_par_id[cid]) for cid in equipe_a_ids]
    )
    partie.joueur_ia = Joueur(
        "ia", True, [CombattantEnEquipe(templates_par_id[cid]) for cid in equipe_b_ids]
    )
    partie.joueur_humain.pv = PV_DEPART
    partie.joueur_ia.pv = PV_DEPART

    partie.duel_numero = 1
    partie.j1 = None
    partie.j2 = None
    partie.combattant_j1 = None
    partie.combattant_j2 = None
    partie.deck_cartes = []
    partie.cartes_j1 = []
    partie.cartes_j2 = []
    partie.arrete_j1 = False
    partie.arrete_j2 = False
    partie.force_j1 = False
    partie.force_j2 = False
    partie.tour_pioche = None
    partie.phase = "choix_combattant"
    partie.dernier_resultat = None
    partie.historique = []
    partie.masque_premiere_carte = {"j1": False, "j2": False}
    partie.revele_types = {"j1": set(), "j2": set()}
    partie.revele_premiere = {"j1": False, "j2": False}
    partie.evenements_pioche = []
    partie.terminee = False
    partie.vainqueur = None

    partie.j1 = random.choice([partie.joueur_humain, partie.joueur_ia])
    partie.j2 = partie.joueur_ia if partie.j1 is partie.joueur_humain else partie.joueur_humain
    partie._auto_choix_ia_si_necessaire()
    return partie


def jouer_partie_libre(partie):
    """Joue une partie complete construite via construire_partie_libre, les deux
    camps pilotes par l'heuristique IA existante (meme pattern que
    analyse_matchups.py / generate_metagame.py)."""

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

    return partie.vainqueur


def tester_personnage(templates, cible_id, n_parties):
    """Simule n_parties parties pour le personnage cible, dans un environnement
    homogene du rang de reference associe a son rang. Renvoie (victoires, parties)
    du point de vue de l'equipe du personnage cible."""
    niveau = templates[cible_id].niveau
    rang_ref = RANG_REFERENCE[niveau]
    pool_ref = [cid for cid, t in templates.items() if t.niveau == rang_ref]

    if len(pool_ref) < 7:
        raise RuntimeError(
            f"Pas assez de personnages de rang {rang_ref} ({len(pool_ref)}) pour "
            f"composer deux equipes distinctes (3 + 4 requis)"
        )

    victoires = 0.0
    for _ in range(n_parties):
        fillers_a = random.sample(pool_ref, 3)
        reste = [cid for cid in pool_ref if cid not in fillers_a]
        equipe_b_ids = random.sample(reste, 4)
        equipe_a_ids = [cible_id] + fillers_a

        partie = construire_partie_libre(templates, equipe_a_ids, equipe_b_ids)
        vainqueur = jouer_partie_libre(partie)

        if vainqueur == "humain":
            victoires += 1
        elif vainqueur is None:
            victoires += 0.5

    return victoires, n_parties


def ecrire_csv_resume(chemin, lignes_resume):
    with open(chemin, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "combattant", "niveau", "rang_reference", "parties", "victoires",
            "taux_victoire_equipe_pct", "direction_attendue",
        ])
        for r in lignes_resume:
            writer.writerow([
                r["nom"], r["niveau"], r["rang_ref"], r["parties"], r["victoires"],
                f"{r['taux']:.1f}", r["direction_attendue"],
            ])


def main():
    parser = argparse.ArgumentParser(
        description="Teste la coherence des rangs des Combattants : plonge chaque "
        "personnage dans un environnement homogene d'un rang de reference et mesure "
        "le taux de victoire d'equipe resultant."
    )
    parser.add_argument("--n-parties", type=int, default=N_PARTIES_DEFAUT,
                         help=f"Parties simulees par personnage (defaut : {N_PARTIES_DEFAUT})")
    parser.add_argument("--sortie-dir", default=BASE_DIR,
                         help="Dossier de sortie pour le CSV (defaut : racine du projet)")
    parser.add_argument("--personnage", default=None,
                         help="Ne tester qu'un seul personnage, par son nom (insensible a la casse). "
                              "Par defaut, tous les personnages sont testes.")
    args = parser.parse_args()

    templates = charger_combattants(DATA_PATH)
    ids = list(templates.keys())

    if args.personnage is not None:
        recherche = args.personnage.casefold()
        ids = [cid for cid in ids if templates[cid].nom.casefold() == recherche]
        if not ids:
            noms_disponibles = ", ".join(sorted(t.nom for t in templates.values()))
            print(f"Aucun personnage nomme '{args.personnage}'. Disponibles : {noms_disponibles}", file=sys.stderr)
            sys.exit(1)

    print(f"Chargement de {len(ids)} Combattants depuis {DATA_PATH}", file=sys.stderr)
    print(f"Test de coherence des rangs ({args.n_parties} parties/personnage)", file=sys.stderr)

    lignes_resume = []
    palier = max(1, len(ids) // 10)
    for i, cible_id in enumerate(ids):
        niveau = templates[cible_id].niveau
        rang_ref = RANG_REFERENCE[niveau]
        victoires, parties = tester_personnage(templates, cible_id, args.n_parties)
        taux = 100 * victoires / parties if parties else 0.0
        lignes_resume.append({
            "nom": templates[cible_id].nom,
            "niveau": niveau,
            "rang_ref": rang_ref,
            "parties": parties,
            "victoires": victoires,
            "taux": taux,
            "direction_attendue": DIRECTION_ATTENDUE[niveau],
        })
        if (i + 1) % palier == 0:
            print(f"... {i + 1}/{len(ids)} personnages testes", file=sys.stderr)

    os.makedirs(args.sortie_dir, exist_ok=True)
    chemin_resume = os.path.join(args.sortie_dir, "coherence_rangs_resume.csv")
    ecrire_csv_resume(chemin_resume, lignes_resume)

    lignes_resume.sort(key=lambda r: (r["niveau"], -r["taux"]))
    largeur_nom = max(len(r["nom"]) for r in lignes_resume)

    print(f"\nCoherence des rangs ({args.n_parties} parties/personnage)\n")
    entete = (
        f"{'Combattant':<{largeur_nom}}  {'Rang':>4}  {'Rang ref.':>9}  {'Parties':>8}  "
        f"{'% Victoire equipe':>18}  {'Attendu':>8}"
    )
    print(entete)
    print("-" * len(entete))
    for r in lignes_resume:
        print(
            f"{r['nom']:<{largeur_nom}}  {r['niveau']:>4}  {r['rang_ref']:>9}  {r['parties']:>8}  "
            f"{r['taux']:>17.1f}%  {r['direction_attendue']:>8}"
        )

    print("\nSynthese par rang (moyenne du taux de victoire d'equipe)\n")
    for niveau in sorted(RANG_REFERENCE):
        taux_niveau = [r["taux"] for r in lignes_resume if r["niveau"] == niveau]
        if not taux_niveau:
            continue
        moyenne = sum(taux_niveau) / len(taux_niveau)
        print(
            f"Rang {niveau} (reference rang {RANG_REFERENCE[niveau]}) : "
            f"moyenne {moyenne:.1f}% (attendu {DIRECTION_ATTENDUE[niveau]}), "
            f"min {min(taux_niveau):.1f}% / max {max(taux_niveau):.1f}%"
        )

    print(f"\nResume par personnage : {chemin_resume}")


if __name__ == "__main__":
    main()
