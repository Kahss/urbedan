"""Orchestration d'une Partie d'Urban Eredan : mise en place, tour de jeu, IA."""
import json
import random

from .ia import choisir_combattant, decider_piocher_ou_arreter
from .models import CombattantEnEquipe, CombattantTemplate, Joueur, construire_deck_cartes_puissance
from .powers import resoudre_duel

NB_DUELS_MAX = 4
PV_DEPART = 10
NIVEAU_TOTAL_MAX = 8


class ErreurPartie(Exception):
    pass


def charger_combattants(chemin_json):
    with open(chemin_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {c["id"]: CombattantTemplate(c) for c in data["combattants"]}


def tirer_equipe_equilibree(templates_par_id, ids_exclus=(), niveau_total_max=NIVEAU_TOTAL_MAX, max_tentatives=200):
    """Tire au hasard 4 ids de Combattants (parmi ceux non exclus) dont la somme des
    niveaux ne depasse pas `niveau_total_max`. Repli si aucun tirage aleatoire n'y
    parvient en `max_tentatives` essais : les 4 niveaux les plus bas disponibles,
    qui respectent toujours la contrainte des lors qu'une equipe valide existe."""
    ids_exclus = set(ids_exclus)
    candidats = [cid for cid in templates_par_id if cid not in ids_exclus]
    for _ in range(max_tentatives):
        echantillon = random.sample(candidats, 4)
        if sum(templates_par_id[cid].niveau for cid in echantillon) <= niveau_total_max:
            return echantillon
    return sorted(candidats, key=lambda cid: templates_par_id[cid].niveau)[:4]


class Partie:
    def __init__(self, templates_par_id, equipe_joueur_ids):
        if len(equipe_joueur_ids) != 4 or len(set(equipe_joueur_ids)) != 4:
            raise ErreurPartie("L'equipe du joueur doit comporter 4 Combattants distincts")
        for cid in equipe_joueur_ids:
            if cid not in templates_par_id:
                raise ErreurPartie(f"Combattant inconnu : {cid}")

        niveau_total = sum(templates_par_id[cid].niveau for cid in equipe_joueur_ids)
        if niveau_total > NIVEAU_TOTAL_MAX:
            raise ErreurPartie(
                f"La somme des niveaux de l'equipe ne peut pas depasser {NIVEAU_TOTAL_MAX} (actuelle : {niveau_total})"
            )

        equipe_ia_ids = tirer_equipe_equilibree(templates_par_id, equipe_joueur_ids)

        self.joueur_humain = Joueur(
            "humain", False, [CombattantEnEquipe(templates_par_id[cid]) for cid in equipe_joueur_ids]
        )
        self.joueur_ia = Joueur(
            "ia", True, [CombattantEnEquipe(templates_par_id[cid]) for cid in equipe_ia_ids]
        )
        self.joueur_humain.pv = PV_DEPART
        self.joueur_ia.pv = PV_DEPART

        self.duel_numero = 1
        self.j1 = None
        self.j2 = None
        self.combattant_j1 = None
        self.combattant_j2 = None
        self.deck_cartes = []
        self.cartes_j1 = []
        self.cartes_j2 = []
        self.arrete_j1 = False
        self.arrete_j2 = False
        self.force_j1 = False
        self.force_j2 = False
        self.tour_pioche = None
        self.phase = "choix_combattant"
        self.dernier_resultat = None
        self.historique = []
        self.terminee = False
        self.vainqueur = None

        self.j1 = random.choice([self.joueur_humain, self.joueur_ia])
        self.j2 = self.joueur_ia if self.j1 is self.joueur_humain else self.joueur_humain
        self._auto_choix_ia_si_necessaire()

    # ------------------------------------------------------------------ IA
    def _auto_choix_ia_si_necessaire(self):
        if self.j1.est_ia and self.combattant_j1 is None:
            self._choix_ia(self.j1, "j1", "combattant_j1")
        if self.j2.est_ia and self.combattant_j2 is None and self.combattant_j1 is not None:
            self._choix_ia(self.j2, "j2", "combattant_j2")

    def _choix_ia(self, joueur, role, attr_combattant):
        """L'IA choisit, via une heuristique simple (cf. ia.py), le Combattant qui
        maximise la Puissance totale estimee pour ce duel."""
        adversaire = self.joueur_ia if joueur is self.joueur_humain else self.joueur_humain
        instance = choisir_combattant(joueur, role, self.duel_numero, NB_DUELS_MAX, joueur.pv, adversaire.pv)
        setattr(self, attr_combattant, instance)

    def _auto_pioche_ia_si_necessaire(self):
        """Fait jouer automatiquement l'IA tant que c'est son tour de decider de
        piocher ou de s'arreter (meme pattern que le choix de Combattant)."""
        while self.phase == "pioche" and not (self.arrete_j1 and self.arrete_j2):
            joueur_du_tour = self.j1 if self.tour_pioche == "j1" else self.j2
            if not joueur_du_tour.est_ia:
                return
            action = decider_piocher_ou_arreter(
                self._cartes(self.tour_pioche), self._malus(self.tour_pioche), list(self.deck_cartes)
            )
            self._appliquer_decision_pioche(self.tour_pioche, action)

    # ---------------------------------------------------------------- pioche
    def _cartes(self, slot):
        return self.cartes_j1 if slot == "j1" else self.cartes_j2

    def _malus(self, slot):
        return sum(c.malus for c in self._cartes(slot))

    def _est_arrete(self, slot):
        return self.arrete_j1 if slot == "j1" else self.arrete_j2

    def _demarrer_pioche(self):
        self.deck_cartes = construire_deck_cartes_puissance()
        self.cartes_j1 = []
        self.cartes_j2 = []
        self.arrete_j1 = False
        self.arrete_j2 = False
        self.force_j1 = False
        self.force_j2 = False
        self.tour_pioche = "j1"
        self.phase = "pioche"
        self._auto_pioche_ia_si_necessaire()

    def _appliquer_decision_pioche(self, slot, action):
        if action == "piocher":
            if not self.deck_cartes:
                raise ErreurPartie("Le tas de Cartes Puissance est epuise")
            carte = self.deck_cartes.pop()
            self._cartes(slot).append(carte)
            if self._malus(slot) >= 3:
                self._forcer_arret(slot)
        elif action == "arreter":
            self._marquer_arrete(slot)
        else:
            raise ErreurPartie("Action de pioche inconnue")

        if self.arrete_j1 and self.arrete_j2:
            self._resoudre_duel_courant()
            return

        autre = "j2" if slot == "j1" else "j1"
        if not self._est_arrete(autre):
            self.tour_pioche = autre
        # sinon le joueur qui vient de jouer garde la main (l'autre a deja fini)

    def _marquer_arrete(self, slot):
        if slot == "j1":
            self.arrete_j1 = True
        else:
            self.arrete_j2 = True

    def _forcer_arret(self, slot):
        self._marquer_arrete(slot)
        if slot == "j1":
            self.force_j1 = True
        else:
            self.force_j2 = True

    # ------------------------------------------------------------ actions
    def soumettre_combattant(self, combattant_id):
        if self.phase != "choix_combattant":
            raise ErreurPartie("Ce n'est pas la phase de choix du Combattant")

        if self.j1 is self.joueur_humain:
            cible_joueur, attr_combattant = self.j1, "combattant_j1"
        else:
            if self.combattant_j1 is None:
                raise ErreurPartie("En attente du choix de Combattant de l'IA")
            cible_joueur, attr_combattant = self.j2, "combattant_j2"

        if getattr(self, attr_combattant) is not None:
            raise ErreurPartie("Le Combattant humain a deja ete choisi pour ce duel")

        instance = next((c for c in cible_joueur.combattants_disponibles() if c.template.id == combattant_id), None)
        if instance is None:
            raise ErreurPartie("Combattant indisponible")

        setattr(self, attr_combattant, instance)

        self._auto_choix_ia_si_necessaire()
        if self.combattant_j1 is not None and self.combattant_j2 is not None:
            self._demarrer_pioche()
        return self.etat_dict()

    def decider_pioche(self, action):
        if self.phase != "pioche":
            raise ErreurPartie("Ce n'est pas la phase de pioche")

        slot_humain = "j1" if self.j1 is self.joueur_humain else "j2"
        if self._est_arrete(slot_humain):
            raise ErreurPartie("Le joueur humain a deja arrete de piocher pour ce duel")
        if self.tour_pioche != slot_humain:
            raise ErreurPartie("Ce n'est pas le tour du joueur humain")

        self._appliquer_decision_pioche(slot_humain, action)
        self._auto_pioche_ia_si_necessaire()
        return self.etat_dict()

    def _resoudre_duel_courant(self):
        joueur_humain_est_j1 = self.j1 is self.joueur_humain
        cartes_j1 = self.cartes_j1
        cartes_j2 = self.cartes_j2

        resultat = resoudre_duel(
            self.j1, self.combattant_j1, cartes_j1,
            self.j2, self.combattant_j2, cartes_j2,
            self.duel_numero, NB_DUELS_MAX,
        )
        self.combattant_j1.utilise = True
        self.combattant_j2.utilise = True
        resultat["duel_numero"] = self.duel_numero
        resultat["combattant_j1"] = self._info_combattant_resultat(cartes_j1, joueur_humain_est_j1)
        resultat["combattant_j2"] = self._info_combattant_resultat(cartes_j2, not joueur_humain_est_j1)
        self.dernier_resultat = resultat
        self.historique.append(resultat)
        self.phase = "duel_resolu"

        self._verifier_fin_partie(fin_de_manche=(self.duel_numero >= NB_DUELS_MAX))

    def _info_combattant_resultat(self, cartes, est_humain):
        malus_total = sum(c.malus for c in cartes)
        busted = malus_total >= 3
        return {
            "role": "humain" if est_humain else "ia",
            "cartes": [c.to_dict() for c in cartes],
            "puissance_cartes": 0 if busted else sum(c.puissance for c in cartes),
            "malus_total": malus_total,
            "busted": busted,
        }

    def duel_suivant(self):
        if self.phase != "duel_resolu":
            raise ErreurPartie("Le duel courant n'est pas termine")
        if self.terminee:
            return self.etat_dict()

        gagnants_ids = self.dernier_resultat["gagnants_ids"]
        double_victoire = len(gagnants_ids) == 2
        if double_victoire:
            self.j1, self.j2 = self.j2, self.j1
        else:
            gagnant_est_j1 = self.combattant_j1.template.id == gagnants_ids[0]
            if not gagnant_est_j1:
                self.j1, self.j2 = self.j2, self.j1

        self.duel_numero += 1
        self.combattant_j1 = None
        self.combattant_j2 = None
        self.deck_cartes = []
        self.cartes_j1 = []
        self.cartes_j2 = []
        self.arrete_j1 = False
        self.arrete_j2 = False
        self.force_j1 = False
        self.force_j2 = False
        self.tour_pioche = None
        self.dernier_resultat = None
        self.phase = "choix_combattant"
        self._auto_choix_ia_si_necessaire()
        return self.etat_dict()

    def _verifier_fin_partie(self, fin_de_manche):
        pv_h = self.joueur_humain.pv
        pv_i = self.joueur_ia.pv
        if pv_h <= 0 or pv_i <= 0:
            self.terminee = True
            if pv_h <= 0 and pv_i <= 0:
                self.vainqueur = None
            elif pv_h <= 0:
                self.vainqueur = "ia"
            else:
                self.vainqueur = "humain"
        elif fin_de_manche:
            self.terminee = True
            if pv_h > pv_i:
                self.vainqueur = "humain"
            elif pv_i > pv_h:
                self.vainqueur = "ia"
            else:
                self.vainqueur = None

    # ---------------------------------------------------------------- etat
    def _info_pioche(self, slot):
        """Info de pioche exposee pour un slot (j1/j2) : detail complet pour le
        joueur humain, seulement le nombre de cartes et l'arret pour l'IA (les
        cartes de l'adversaire restent cachees jusqu'a la resolution du duel)."""
        est_humain = (self.j1 if slot == "j1" else self.j2) is self.joueur_humain
        cartes = self._cartes(slot)
        arrete = self._est_arrete(slot)
        if est_humain:
            malus_total = sum(c.malus for c in cartes)
            return {
                "cartes": [c.to_dict() for c in cartes],
                "puissance_cartes": 0 if malus_total >= 3 else sum(c.puissance for c in cartes),
                "malus_total": malus_total,
                "nb_cartes": len(cartes),
                "arrete": arrete,
            }
        return {"nb_cartes": len(cartes), "arrete": arrete}

    def etat_dict(self):
        return {
            "phase": self.phase,
            "duel_numero": self.duel_numero,
            "duels_max": NB_DUELS_MAX,
            "j1": "humain" if self.j1 is self.joueur_humain else "ia",
            "joueur_humain": self.joueur_humain.to_dict(),
            "joueur_ia": self.joueur_ia.to_dict(),
            "combattant_j1": self.combattant_j1.template.id if self.combattant_j1 else None,
            "combattant_j2": self.combattant_j2.template.id if self.combattant_j2 else None,
            "pioche": {
                "tour": self.tour_pioche,
                "cartes_restantes_deck": len(self.deck_cartes),
                "j1": self._info_pioche("j1"),
                "j2": self._info_pioche("j2"),
            },
            "dernier_resultat": self.dernier_resultat,
            "terminee": self.terminee,
            "vainqueur": self.vainqueur,
        }
