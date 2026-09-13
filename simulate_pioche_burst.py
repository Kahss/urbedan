"""Simule un grand nombre de pioches de Cartes Puissance (phase "stop ou encore"),
en piochant jusqu'au Burst (Malus total >= 3), pour etudier la probabilite de
chaque total de Puissance accumulable en jouant "au maximum" (on ne s'arrete
jamais volontairement : on ne s'arrete que force par le Burst).

Reutilise le deck reel du jeu (`engine.models.construire_deck_cartes_puissance`,
20 cartes : Destin, Epreuve, Peripetie, Adversite) : aucune regle n'est
redefinie ici.

Pour chaque pioche, on releve la Puissance totale juste avant la carte qui
declenche le Burst (le total qu'on aurait pu "encaisser" en s'arretant a ce
moment-la) : au-dela, en cas de Burst, la Puissance des cartes est annulee
(cf. `engine.game._info_pioche` / `powers.py`), donc ce dernier total sur
est la seule quantite interessante a etudier.

Usage :
    python simulate_pioche_burst.py -n 10000
"""
import argparse
import os
import sys
from collections import Counter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, "backend"))

from engine.models import construire_deck_cartes_puissance  # noqa: E402

MALUS_BURST = 3


def piocher_jusqu_au_burst():
    """Pioche un deck complet (frais, remelange) jusqu'au Burst (Malus total >= 3)
    ou jusqu'a epuisement du deck (cas limite si le Burst ne survient jamais).
    Retourne (puissance_sure, nb_cartes_piochees, burst) ou `puissance_sure` est
    la Puissance totale accumulee juste avant la carte de Burst (0 si Burst des
    la 1ere carte), et `burst` indique si le deck a ete epuise sans Burst."""
    deck = construire_deck_cartes_puissance()
    malus_total = 0
    puissance_sure = 0
    nb_cartes = 0
    for carte in deck:
        nb_cartes += 1
        if malus_total + carte.malus >= MALUS_BURST:
            return puissance_sure, nb_cartes, True
        malus_total += carte.malus
        puissance_sure += carte.puissance
    return puissance_sure, nb_cartes, False


def histogramme_ascii(compteur, total, largeur_max=40):
    lignes = []
    valeur_max = max(compteur.values())
    for valeur in sorted(compteur):
        n = compteur[valeur]
        pct = n / total * 100
        barre = "#" * max(1, round(n / valeur_max * largeur_max))
        lignes.append(f"{valeur:>3}  {n:>6}  {pct:>6.2f}%  {barre}")
    return "\n".join(lignes)


def main():
    parser = argparse.ArgumentParser(
        description="Simule des pioches de Cartes Puissance jusqu'au Burst et dresse "
        "la distribution de probabilite de la Puissance sure accumulable."
    )
    parser.add_argument(
        "-n", "--nombre-tirages", type=int, default=10000,
        help="Nombre de pioches (parties de pioche) a simuler (defaut : 10000)",
    )
    args = parser.parse_args()

    compteur_puissance = Counter()
    compteur_nb_cartes = Counter()
    nb_deck_epuise = 0

    for _ in range(args.nombre_tirages):
        puissance_sure, nb_cartes, burst = piocher_jusqu_au_burst()
        compteur_puissance[puissance_sure] += 1
        compteur_nb_cartes[nb_cartes] += 1
        if not burst:
            nb_deck_epuise += 1

    total = args.nombre_tirages
    moyenne = sum(v * n for v, n in compteur_puissance.items()) / total
    moyenne_cartes = sum(v * n for v, n in compteur_nb_cartes.items()) / total

    print(f"\n{total} pioches simulees (jusqu'au Burst, Malus total >= {MALUS_BURST})\n")
    print("Distribution de la Puissance sure accumulee juste avant le Burst")
    print("(le total qu'on aurait pu encaisser en s'arretant a ce moment) :\n")
    print(f"{'Puiss.':>3}  {'Nb':>6}  {'% des tirages':>6}   Histogramme")
    print(histogramme_ascii(compteur_puissance, total))
    print(f"\nMoyenne : {moyenne:.2f} de Puissance sure avant Burst")

    print("\nDistribution du nombre de Cartes Puissance piochees avant le Burst :\n")
    print(f"{'Cartes':>3}  {'Nb':>6}  {'% des tirages':>6}   Histogramme")
    print(histogramme_ascii(compteur_nb_cartes, total))
    print(f"\nMoyenne : {moyenne_cartes:.2f} cartes piochees avant Burst")

    if nb_deck_epuise:
        print(
            f"\n{nb_deck_epuise} tirage(s) sur {total} ont epuise le deck de 20 cartes "
            "sans jamais Burst (cas limite)."
        )


if __name__ == "__main__":
    main()
