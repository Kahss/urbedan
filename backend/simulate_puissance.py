"""Simulateur de parties : etudie la puissance des Combattants (taux de victoire
des equipes dont ils ont fait partie) en fonction de leur rang (niveau 1 a 3).

Reutilise integralement le moteur de jeu (`engine.game.Partie`) et les
heuristiques de l'IA (`engine.ia`) : les deux equipes sont pilotees par l'IA
existante (choix du Combattant, decision pioche/arret), aucune regle du jeu
n'est reimplementee ici.

Usage : python3 simulate_puissance.py [nb_parties]  (depuis le dossier backend/)
"""
import os
import sys
from collections import defaultdict

from engine.game import NB_DUELS_MAX, Partie, charger_combattants, tirer_equipe_equilibree
from engine.ia import choisir_combattant, decider_piocher_ou_arreter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "..", "data", "combattants.json")
NB_PARTIES_DEFAUT = 20000


def jouer_partie_auto(templates_par_id, equipe_a_ids):
    """Joue une Partie entierement en automatique : l'equipe "ia" est deja pilotee
    par le moteur existant ; l'equipe "humain" est ici pilotee avec les memes
    heuristiques (`choisir_combattant` / `decider_piocher_ou_arreter`), en passant
    uniquement par l'API publique de `Partie` (soumettre_combattant / decider_pioche)."""
    partie = Partie(templates_par_id, equipe_a_ids)
    while not partie.terminee:
        if partie.phase == "choix_combattant":
            if partie.j1 is partie.joueur_humain and partie.combattant_j1 is None:
                role, joueur, adversaire = "j1", partie.joueur_humain, partie.joueur_ia
            elif partie.j2 is partie.joueur_humain and partie.combattant_j2 is None:
                role, joueur, adversaire = "j2", partie.joueur_humain, partie.joueur_ia
            else:
                raise RuntimeError("etat inattendu en phase choix_combattant")
            instance = choisir_combattant(joueur, role, partie.duel_numero, NB_DUELS_MAX, joueur.pv, adversaire.pv)
            partie.soumettre_combattant(instance.template.id)
        elif partie.phase == "pioche":
            slot_humain = "j1" if partie.j1 is partie.joueur_humain else "j2"
            cartes = partie.cartes_j1 if slot_humain == "j1" else partie.cartes_j2
            malus = sum(c.malus for c in cartes)
            action = decider_piocher_ou_arreter(cartes, malus, list(partie.deck_cartes))
            partie.decider_pioche(action)
        elif partie.phase == "duel_resolu":
            partie.duel_suivant()
        else:
            raise RuntimeError(f"phase inattendue : {partie.phase}")
    return partie


def simuler(templates_par_id, nb_parties):
    stats = {
        cid: {"nom": t.nom, "niveau": t.niveau, "participations": 0, "victoires": 0, "defaites": 0, "nuls": 0}
        for cid, t in templates_par_id.items()
    }

    def enregistrer(equipe_ids, resultat):
        for cid in equipe_ids:
            s = stats[cid]
            s["participations"] += 1
            if resultat == "victoire":
                s["victoires"] += 1
            elif resultat == "defaite":
                s["defaites"] += 1
            else:
                s["nuls"] += 1

    for _ in range(nb_parties):
        equipe_a_ids = tirer_equipe_equilibree(templates_par_id)
        partie = jouer_partie_auto(templates_par_id, equipe_a_ids)
        equipe_b_ids = [c.template.id for c in partie.joueur_ia.equipe]

        if partie.vainqueur == "humain":
            resultat_a, resultat_b = "victoire", "defaite"
        elif partie.vainqueur == "ia":
            resultat_a, resultat_b = "defaite", "victoire"
        else:
            resultat_a, resultat_b = "nul", "nul"

        enregistrer(equipe_a_ids, resultat_a)
        enregistrer(equipe_b_ids, resultat_b)

    return stats


def generer_rapport(stats, nb_parties):
    lignes = []
    lignes.append(f"# Rapport de simulation : puissance des Combattants par rang\n")
    lignes.append(f"{nb_parties} parties simulees (equipes de 4, niveau total <= 8, "
                   f"equipes tirees et jouees automatiquement par l'IA existante).\n")

    for niveau in (3, 2, 1):
        lignes.append(f"\n## Rang {niveau}\n")
        lignes.append("| Combattant | Participations | Victoires | Defaites | Nuls | % Victoire |")
        lignes.append("|---|---|---|---|---|---|")
        combattants_du_rang = [s for s in stats.values() if s["niveau"] == niveau]
        combattants_du_rang.sort(
            key=lambda s: (s["victoires"] / s["participations"] if s["participations"] else 0),
            reverse=True,
        )
        for s in combattants_du_rang:
            pct = 100 * s["victoires"] / s["participations"] if s["participations"] else 0.0
            lignes.append(
                f"| {s['nom']} | {s['participations']} | {s['victoires']} | {s['defaites']} | {s['nuls']} | {pct:.1f}% |"
            )

    lignes.append("\n## Moyenne par rang\n")
    lignes.append("| Rang | % Victoire moyen |")
    lignes.append("|---|---|")
    for niveau in (3, 2, 1):
        combattants_du_rang = [s for s in stats.values() if s["niveau"] == niveau]
        pcts = [100 * s["victoires"] / s["participations"] for s in combattants_du_rang if s["participations"]]
        moyenne = sum(pcts) / len(pcts) if pcts else 0.0
        lignes.append(f"| {niveau} | {moyenne:.1f}% |")

    return "\n".join(lignes) + "\n"


def main():
    nb_parties = int(sys.argv[1]) if len(sys.argv) > 1 else NB_PARTIES_DEFAUT
    templates_par_id = charger_combattants(DATA_PATH)
    stats = simuler(templates_par_id, nb_parties)
    rapport = generer_rapport(stats, nb_parties)
    print(rapport)


if __name__ == "__main__":
    main()
