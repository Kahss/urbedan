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
import random
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, "backend"))

from engine.game import Partie, charger_combattants  # noqa: E402
from engine.ia import choisir_combattant  # noqa: E402

DATA_PATH = os.path.join(BASE_DIR, "data", "combattants.json")


def role_humain(partie):
    return "j1" if partie.j1 is partie.joueur_humain else "j2"


def jouer_choix_humain(partie):
    """Fait engager au joueur 'humain' de la partie son Combattant pour le duel en cours,
    via la meme heuristique que l'IA (cf. engine/ia.py), de maniere a simuler un
    affrontement IA contre IA."""
    role = role_humain(partie)
    if getattr(partie, "combattant_" + role) is not None:
        return
    instance = choisir_combattant(partie.joueur_humain)
    partie.soumettre_combattant(instance.template.id)


def jouer_pioche_humaine(partie):
    """Fait choisir au joueur 'humain' l'une des 2 pioches de cartes Bataille, avec la
    meme heuristique que l'IA."""
    partie.soumettre_pioche(partie.choisir_pioche_ia(role_humain(partie)))


def jouer_partie(templates, tous_les_ids):
    """Joue une partie complete (equipes tirees au hasard dans tout le roster) et
    retourne (ids equipe A, ids equipe B, vainqueur : 'humain' / 'ia' / None)."""
    equipe_a = random.sample(tous_les_ids, 4)
    partie = Partie(templates, equipe_a)
    equipe_b = [c.template.id for c in partie.joueur_ia.equipe]

    while not partie.terminee:
        if partie.phase == "choix_combattant":
            jouer_choix_humain(partie)
        elif partie.phase == "batailles" and partie.role_actif == role_humain(partie):
            jouer_pioche_humaine(partie)
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
        lignes.append((templates[cid].nom, parties, victoires, taux))
    lignes.sort(key=lambda ligne: ligne[3], reverse=True)

    largeur_nom = max(len(nom) for nom, _, _, _ in lignes)
    print(f"\nStatistiques sur {args.nombre_parties} parties simulees (IA contre IA)\n")
    entete = f"{'Combattant':<{largeur_nom}}  {'Parties':>8}  {'Victoires':>9}  {'% Victoire':>10}"
    print(entete)
    print("-" * len(entete))
    for nom, parties, victoires, taux in lignes:
        print(f"{nom:<{largeur_nom}}  {parties:>8}  {victoires:>9}  {taux:>9.2f}%")


if __name__ == "__main__":
    main()
