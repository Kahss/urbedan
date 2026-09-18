"""Auto-check de la regle "pioche libre + se coucher" (cf. README/CLAUDE : plus
d'arret automatique a 3 de Malus, perte de PV = Malus accumule a la resolution,
sauf pour un Combattant couche qui annule l'entierete de ses cartes piochees).

Usage : cd backend && python3 test_pioche_couche.py
"""
from engine.game import ErreurPartie, Partie
from engine.ia import decider_piocher_ou_arreter
from engine.models import (
    CartePuissance,
    CombattantEnEquipe,
    CombattantTemplate,
    Joueur,
    construire_deck_cartes_puissance,
)
from engine.powers import resoudre_duel


def _template(nom, puissance=1, degats=1):
    return CombattantTemplate({
        "id": nom, "nom": nom, "puissance": puissance, "degats": degats, "niveau": 1,
        "pouvoir": {"description": "", "condition": None, "modificateur": None, "effets": []},
    })


def _joueur(nom, template):
    return Joueur(nom, False, [CombattantEnEquipe(template)])


def test_malus_coute_des_pv_sans_se_coucher():
    j1, j2 = _joueur("j1", _template("A", degats=0)), _joueur("j2", _template("B", degats=0))
    cartes_j1 = [CartePuissance("Adversite", 1, 2), CartePuissance("Epreuve", 1, 1)]  # +2 puissance, 3 malus
    resoudre_duel(j1, j1.equipe[0], cartes_j1, j2, j2.equipe[0], [], 1, 4)
    assert j1.pv == 7, f"j1.pv={j1.pv} (attendu 7 : -3 PV pour son Malus, pas de degats car degats=0)"
    assert j2.pv == 10, f"j2.pv={j2.pv} (aucun Malus, aucun degat)"


def test_se_coucher_annule_puissance_et_malus():
    j1, j2 = _joueur("j1", _template("A", degats=0)), _joueur("j2", _template("B", degats=0))
    cartes_j1 = [CartePuissance("Adversite", 1, 2), CartePuissance("Epreuve", 1, 1)]
    resoudre_duel(j1, j1.equipe[0], cartes_j1, j2, j2.equipe[0], [], 1, 4, couche_j1=True)
    assert j1.pv == 10, f"j1.pv={j1.pv} (couche : ni gain de puissance ni perte de PV liee au Malus)"
    assert j2.pv == 10


def test_se_coucher_n_annule_pas_le_reste_de_la_resolution():
    # Degats non nuls : si le fold annule le Malus/la Puissance des cartes mais pas
    # le reste, une egalite de Puissance de base (double victoire) inflige toujours
    # les Degats normalement, cote comme cote.
    j1, j2 = _joueur("j1", _template("A", degats=1)), _joueur("j2", _template("B", degats=1))
    cartes_j1 = [CartePuissance("Adversite", 1, 2)]
    resultat = resoudre_duel(j1, j1.equipe[0], cartes_j1, j2, j2.equipe[0], [], 1, 4, couche_j1=True)
    assert set(resultat["gagnants_ids"]) == {"A", "B"}, "puissance de base egale -> double victoire"
    assert j1.pv == 9, f"j1.pv={j1.pv} (subit toujours les Degats de B, malgre le fold)"
    assert j2.pv == 9, f"j2.pv={j2.pv} (subit toujours les Degats de A)"


def _template_surcharge(nom, puissance):
    return CombattantTemplate({
        "id": nom, "nom": nom, "puissance": puissance, "degats": 0, "niveau": 1,
        "pouvoir": {
            "description": "", "condition": "surcharge", "modificateur": None,
            "effets": [{"type": "vie", "cible": "soi", "valeur": -2}],
        },
    })


def test_surcharge_se_declenche_a_puissance_double_ou_plus():
    fort = _template_surcharge("Fort", 6)  # 6 >= 2 x 3
    faible = _template("Faible", puissance=3, degats=0)  # pas de pouvoir : temoin neutre
    j1, j2 = _joueur("j1", fort), _joueur("j2", faible)
    resoudre_duel(j1, j1.equipe[0], [], j2, j2.equipe[0], [], 1, 4)
    assert j1.pv == 8, f"j1.pv={j1.pv} (surcharge declenchee : -2 PV pour Fort, 6 >= 2x3)"
    assert j2.pv == 10


def test_surcharge_ne_se_declenche_pas_sous_le_double():
    presque = _template_surcharge("Presque", 5)  # 5 < 2 x 3
    adverse = _template("Adverse", puissance=3, degats=0)
    j1, j2 = _joueur("j1", presque), _joueur("j2", adverse)
    resoudre_duel(j1, j1.equipe[0], [], j2, j2.equipe[0], [], 1, 4)
    assert j1.pv == 10, f"j1.pv={j1.pv} (pas de surcharge : 5 < 2x3, pas de perte de PV)"


def test_ia_pioche_sur_un_tas_complet():
    deck_complet = construire_deck_cartes_puissance()
    action = decider_piocher_ou_arreter([], 0, deck_complet, True)
    assert action == "piocher", (
        f"action={action} (le tas de depart est exactement equilibre : 16 de Puissance "
        "pour 16 de Malus sur 20 cartes, une esperance nulle doit donc pousser a piocher, "
        "pas a s'arreter/se coucher immediatement sans jamais avoir pioche)"
    )


def _demarrer_partie_pioche():
    templates = {chr(97 + i): _template(chr(65 + i)) for i in range(10)}
    partie = Partie(templates, ["a", "b", "c", "d"])
    humain_slot = "j1" if partie.j1 is partie.joueur_humain else "j2"
    autre_slot = "j2" if humain_slot == "j1" else "j1"
    disponible = partie.joueur_humain.combattants_disponibles()[0]
    partie.soumettre_combattant(disponible.template.id)
    assert partie.phase == "pioche"
    return partie, humain_slot, autre_slot


def test_pioche_libre_pas_d_arret_force_au_dela_de_3_malus():
    partie, humain_slot, autre_slot = _demarrer_partie_pioche()
    partie._marquer_arrete(autre_slot)  # neutralise le tour de l'IA pour isoler le test
    partie.deck_cartes = [CartePuissance("Adversite", 1, 2) for _ in range(4)]
    for _ in range(4):
        partie._appliquer_decision_pioche(humain_slot, "piocher")
    assert partie._malus_effectif(humain_slot) == 8, "4 cartes a 2 de Malus, largement > 3"
    assert not partie._est_arrete(humain_slot), "la pioche ne doit plus s'arreter automatiquement a 3 de Malus"


def test_se_coucher_impossible_si_adversaire_deja_couche():
    partie, humain_slot, autre_slot = _demarrer_partie_pioche()
    partie._marquer_couche(autre_slot)
    try:
        partie._appliquer_decision_pioche(humain_slot, "se_coucher")
    except ErreurPartie:
        pass
    else:
        raise AssertionError("se coucher aurait du etre refuse (l'adversaire s'est deja couche)")


if __name__ == "__main__":
    for nom, fonction in list(globals().items()):
        if nom.startswith("test_") and callable(fonction):
            fonction()
            print(f"OK {nom}")
    print("Tous les checks sont passes.")
