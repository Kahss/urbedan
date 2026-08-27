"""Simule un grand nombre de matchs d'Urban Eredan (version Eredice) joues entierement
par l'IA des deux cotes (la meme heuristique que `engine/ia.py`) et dresse les
statistiques de pourcentage de victoire de chaque Personnage.

Un Personnage est considere comme gagnant des lors que l'equipe dont il fait partie
remporte le match, conformement au critere d'equilibrage retenu pour le jeu.

Usage :
    python generate_metagame.py -n 2000
"""
import argparse
import os
import random
import sys
from collections import Counter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, "backend"))

from engine.game import TAILLE_EQUIPE, Partie  # noqa: E402
from engine.ia import arbitrer_capacite, choisir_action  # noqa: E402
from engine.models import charger_personnages  # noqa: E402

DATA_PATH = os.path.join(BASE_DIR, "data", "personnages.json")


def jouer_match(templates, tous_les_ids):
    """Joue un match complet (equipes tirees au hasard dans tout le roster), les deux
    camps etant pilotes par l'heuristique de `engine/ia.py`.

    Retourne (ids equipe humaine, ids equipe ia, vainqueur, nombre de rounds)."""
    equipe_a = random.sample(tous_les_ids, TAILLE_EQUIPE)
    partie = Partie(templates, equipe_a)
    equipe_b = [p.template.id for p in partie.joueur_ia.equipe]

    while not partie.terminee:
        creneau = partie.creneau_courant()
        if creneau is None:
            break
        if creneau.joueur.est_ia:
            partie.jouer_creneau_ia()
        else:
            de, perso, usage = choisir_action(partie, creneau.joueur)
            partie.drafter(de.id, perso.template.id, usage)
            # Le camp "humain" est ici pilote par l'IA : les choix entre Capacites
            # payables simultanement, que le moteur laisse au joueur, sont donc tranches
            # avec la meme heuristique que ceux de l'IA.
            while partie.choix_capacite is not None:
                choix = partie.choix_capacite
                partie.choisir_capacite(
                    arbitrer_capacite(choix["personnage"], choix["options"], partie)
                )

    return equipe_a, equipe_b, partie.vainqueur, partie.round_numero


def main():
    parser = argparse.ArgumentParser(
        description="Simule des matchs d'Urban Eredan (Eredice) joues par l'IA et dresse "
        "les statistiques de pourcentage de victoire par Personnage."
    )
    parser.add_argument("-n", "--nombre-matchs", type=int, default=2000,
                        help="Nombre de matchs a simuler (defaut : 2000)")
    args = parser.parse_args()

    templates = charger_personnages(DATA_PATH)
    tous_les_ids = list(templates.keys())
    stats = {pid: {"matchs": 0, "victoires": 0} for pid in tous_les_ids}
    rounds = []
    issues = Counter()

    palier = max(1, args.nombre_matchs // 10)
    for i in range(args.nombre_matchs):
        equipe_a, equipe_b, vainqueur, nb_rounds = jouer_match(templates, tous_les_ids)
        rounds.append(nb_rounds)
        issues[vainqueur or "nul"] += 1
        for pid in equipe_a:
            stats[pid]["matchs"] += 1
            if vainqueur == "humain":
                stats[pid]["victoires"] += 1
        for pid in equipe_b:
            stats[pid]["matchs"] += 1
            if vainqueur == "ia":
                stats[pid]["victoires"] += 1
        if (i + 1) % palier == 0:
            print(f"... {i + 1}/{args.nombre_matchs} matchs simules", file=sys.stderr)

    lignes = []
    for pid in tous_les_ids:
        matchs = stats[pid]["matchs"]
        victoires = stats[pid]["victoires"]
        taux = (victoires / matchs * 100) if matchs else 0.0
        lignes.append((templates[pid].nom, matchs, victoires, taux))
    lignes.sort(key=lambda ligne: ligne[3], reverse=True)

    print(f"\nStatistiques sur {args.nombre_matchs} matchs simules (IA contre IA)")
    print(
        f"Duree moyenne : {sum(rounds) / len(rounds):.2f} rounds "
        f"(min {min(rounds)}, max {max(rounds)}) | issues : {dict(issues)}\n"
    )
    largeur = max(len(nom) for nom, _, _, _ in lignes)
    entete = f"{'Personnage':<{largeur}}  {'Matchs':>7}  {'Victoires':>9}  {'% Victoire':>10}"
    print(entete)
    print("-" * len(entete))
    for nom, matchs, victoires, taux in lignes:
        print(f"{nom:<{largeur}}  {matchs:>7}  {victoires:>9}  {taux:>9.2f}%")


if __name__ == "__main__":
    main()
