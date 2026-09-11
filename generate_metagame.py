"""Simule un grand nombre de parties d'Urban Eredan jouees entierement par l'IA (la
meme heuristique de `engine/ia.py` des deux cotes) et dresse les statistiques de
pourcentage de victoire de chaque Combattant.

Un Combattant est considere comme ayant gagne des lors que l'equipe dont il fait partie
a remporte la partie : il peut avoir perdu son propre duel (voire ne jamais avoir
combattu, si la partie s'est terminee avant que son tour n'arrive), tant que son equipe
a gagne, il compte comme gagnant.

Usage :
    python generate_metagame.py -n 10000
"""
import argparse
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, "backend"))

from engine.game import NB_DUELS_MAX, Partie, charger_combattants, tirer_equipe_equilibree  # noqa: E402
from engine.ia import choisir_combattant, decider_piocher_ou_arreter  # noqa: E402

DATA_PATH = os.path.join(BASE_DIR, "data", "combattants.json")


def jouer_choix_humain(partie):
    """Fait choisir au joueur 'humain' de la partie son Combattant pour le duel en
    cours, via la meme heuristique que l'IA (cf. engine/ia.py), de maniere a simuler
    un affrontement IA contre IA."""
    role = "j1" if partie.j1 is partie.joueur_humain else "j2"
    if getattr(partie, "combattant_" + role) is not None:
        return
    adversaire = partie.joueur_ia
    instance = choisir_combattant(
        partie.joueur_humain, role, partie.duel_numero, NB_DUELS_MAX,
        partie.joueur_humain.pv, adversaire.pv,
    )
    partie.soumettre_combattant(instance.template.id)


def jouer_pioche_humain(partie):
    """Fait decider au joueur 'humain' de la partie, quand c'est son tour, de piocher
    ou de s'arreter pendant la phase 'stop ou encore', via la meme heuristique que
    l'IA (cf. engine/ia.py)."""
    role = "j1" if partie.j1 is partie.joueur_humain else "j2"
    if partie.tour_pioche != role or partie._est_arrete(role):
        return
    action = decider_piocher_ou_arreter(
        partie._cartes(role), partie._malus(role), list(partie.deck_cartes)
    )
    partie.decider_pioche(action)


def jouer_partie(templates, tous_les_ids):
    """Joue une partie complete (equipes tirees au hasard dans tout le roster) et
    retourne (ids equipe A, ids equipe B, vainqueur : 'humain' / 'ia' / None)."""
    equipe_a = tirer_equipe_equilibree(templates)
    partie = Partie(templates, equipe_a)
    equipe_b = [c.template.id for c in partie.joueur_ia.equipe]

    while not partie.terminee:
        if partie.phase == "choix_combattant":
            jouer_choix_humain(partie)
        elif partie.phase == "pioche":
            jouer_pioche_humain(partie)
        elif partie.phase == "duel_resolu":
            partie.duel_suivant()

    return equipe_a, equipe_b, partie.vainqueur


def main():
    parser = argparse.ArgumentParser(
        description="Simule des parties d'Urban Eredan jouees par l'IA et dresse les "
        "statistiques de pourcentage de victoire par Combattant."
    )
    parser.add_argument(
        "-n", "--nombre-parties", type=int, default=10000,
        help="Nombre de parties a simuler (defaut : 10000)",
    )
    args = parser.parse_args()

    templates = charger_combattants(DATA_PATH)
    tous_les_ids = list(templates.keys())

    stats = {cid: {"parties": 0, "victoires": 0} for cid in tous_les_ids}

    palier = max(1, args.nombre_parties // 10)
    for i in range(args.nombre_parties):
        equipe_a, equipe_b, vainqueur = jouer_partie(templates, tous_les_ids)
        for cid in equipe_a:
            stats[cid]["parties"] += 1
            if vainqueur == "humain":
                stats[cid]["victoires"] += 1
        for cid in equipe_b:
            stats[cid]["parties"] += 1
            if vainqueur == "ia":
                stats[cid]["victoires"] += 1
        if (i + 1) % palier == 0:
            print(f"... {i + 1}/{args.nombre_parties} parties simulees", file=sys.stderr)

    lignes = []
    for cid in tous_les_ids:
        parties = stats[cid]["parties"]
        victoires = stats[cid]["victoires"]
        taux = (victoires / parties * 100) if parties else 0.0
        lignes.append((templates[cid].nom, templates[cid].niveau, parties, victoires, taux))
    lignes.sort(key=lambda ligne: ligne[4], reverse=True)

    largeur_nom = max(len(nom) for nom, _, _, _, _ in lignes)
    print(f"\nStatistiques sur {args.nombre_parties} parties simulees (IA contre IA)\n")
    entete = f"{'Combattant':<{largeur_nom}}  {'Rang':>4}  {'Parties':>8}  {'Victoires':>9}  {'% Victoire':>10}"
    print(entete)
    print("-" * len(entete))
    for nom, niveau, parties, victoires, taux in lignes:
        print(f"{nom:<{largeur_nom}}  {niveau:>4}  {parties:>8}  {victoires:>9}  {taux:>9.2f}%")


if __name__ == "__main__":
    main()
