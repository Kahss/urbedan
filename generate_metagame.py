"""Simule un grand nombre de parties d'Urban Eredan (version duo) jouees entierement par
l'IA (la meme heuristique de `engine/ia.py` des deux cotes) et dresse les statistiques de
pourcentage de victoire de chaque Combattant.

Critere d'equilibrage de la version duo (versions/duo.md) : un Combattant est equilibre non
pas s'il remporte la moitie de ses batailles, mais si environ la moitie des equipes dont il
fait partie remporte la partie. Un Combattant compte donc comme gagnant des lors que son
equipe gagne, meme s'il a perdu ses propres batailles (voire s'il n'a jamais ete engage).
C'est ce qui rend viables les Combattants qui ont interet a perdre (Pouvoirs conditionnes
par `defaite`).

Usage :
    python generate_metagame.py -n 10000
"""
import argparse
import os
import random
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, "backend"))

from engine.game import (  # noqa: E402
    NB_BATAILLES_MAX,
    PHASE_BATAILLE_RESOLUE,
    PHASE_CIBLAGE,
    PHASE_CHOIX_DUO,
    Partie,
    charger_combattants,
)
from engine.ia import (  # noqa: E402
    choisir_ciblages,
    choisir_duo,
    estimer_puissance_duo_adverse,
)
from engine.models import TAILLE_EQUIPE  # noqa: E402

DATA_PATH = os.path.join(BASE_DIR, "data", "combattants.json")


def jouer_choix_humain(partie):
    """Fait choisir au camp 'humain' son duo pour la bataille en cours, via la meme
    heuristique que l'IA, en exploitant comme elle les Combattants adverses eventuellement
    reveles par une carte Reperage / Intimidation : les deux camps sont ainsi strictement
    symetriques, sans quoi les statistiques favoriseraient mecaniquement un cote."""
    puissance_adverse = None
    if partie.reveles_ia:
        puissance_adverse = estimer_puissance_duo_adverse(partie.joueur_ia, partie.reveles_ia)
    duo = choisir_duo(
        partie.joueur_humain,
        partie.role_de(partie.joueur_humain),
        partie.tour,
        NB_BATAILLES_MAX,
        partie.joueur_humain.pv,
        partie.joueur_ia.pv,
        partie.batailles_restantes(),
        puissance_adverse_estimee=puissance_adverse,
    )
    partie.soumettre_duo([instance.template.id for instance in duo])


def jouer_partie(templates, tous_les_ids):
    """Joue une partie complete (equipes tirees au hasard dans tout le roster) et
    retourne (ids equipe A, ids equipe B, vainqueur : 'humain' / 'ia' / None)."""
    equipe_a = random.sample(tous_les_ids, TAILLE_EQUIPE)
    partie = Partie(templates, equipe_a)
    equipe_b = [c.template.id for c in partie.joueur_ia.equipe]

    while not partie.terminee:
        if partie.phase == PHASE_CHOIX_DUO:
            jouer_choix_humain(partie)
        elif partie.phase == PHASE_CIBLAGE:
            partie.soumettre_ciblages(
                choisir_ciblages(partie.camp_humain, partie.tour, NB_BATAILLES_MAX)
            )
        elif partie.phase == PHASE_BATAILLE_RESOLUE:
            partie.bataille_suivante()

    return equipe_a, equipe_b, partie.vainqueur


def main():
    parser = argparse.ArgumentParser(
        description="Simule des parties d'Urban Eredan (version duo) jouees par l'IA et "
        "dresse les statistiques de pourcentage de victoire par Combattant."
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
