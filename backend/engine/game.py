"""Orchestration d'une Partie d'Urban Eredan : mise en place, tour de jeu, IA."""
import json
import random

from .models import CombattantEnEquipe, CombattantTemplate, Joueur, construire_deck_glyphes
from .powers import resoudre_duel

NB_DUELS_MAX = 4
PV_DEPART = 12


class ErreurPartie(Exception):
    pass


def charger_combattants(chemin_json):
    with open(chemin_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {c["id"]: CombattantTemplate(c) for c in data["combattants"]}


class Partie:
    def __init__(self, templates_par_id, equipe_joueur_ids):
        if len(equipe_joueur_ids) != 4 or len(set(equipe_joueur_ids)) != 4:
            raise ErreurPartie("L'equipe du joueur doit comporter 4 Combattants distincts")
        for cid in equipe_joueur_ids:
            if cid not in templates_par_id:
                raise ErreurPartie(f"Combattant inconnu : {cid}")

        equipe_ia_ids = [cid for cid in templates_par_id if cid not in equipe_joueur_ids]

        self.joueur_humain = Joueur(
            "humain", False, [CombattantEnEquipe(templates_par_id[cid]) for cid in equipe_joueur_ids]
        )
        self.joueur_ia = Joueur(
            "ia", True, [CombattantEnEquipe(templates_par_id[cid]) for cid in equipe_ia_ids]
        )
        self.joueur_humain.pv = PV_DEPART
        self.joueur_ia.pv = PV_DEPART

        deck = construire_deck_glyphes()
        self.joueur_humain.main = deck[0:5]
        self.joueur_ia.main = deck[5:10]
        # les 2 dernieres cartes du deck restent hors jeu (remises "dans la boite")

        self.duel_numero = 1
        self.j1 = None
        self.j2 = None
        self.combattant_j1 = None
        self.combattant_j2 = None
        self.phase = "choix_combattant"
        self.dernier_resultat = None
        self.historique = []
        self.terminee = False
        self.vainqueur = None

        self.j1 = random.choice([self.joueur_humain, self.joueur_ia])
        self.j2 = self.joueur_ia if self.j1 is self.joueur_humain else self.joueur_humain
        self._auto_choix_combattant_ia_si_necessaire()

    # ------------------------------------------------------------------ IA
    def _auto_choix_combattant_ia_si_necessaire(self):
        if self.j1.est_ia and self.combattant_j1 is None:
            self.combattant_j1 = random.choice(self.j1.combattants_disponibles())
        if self.j2.est_ia and self.combattant_j2 is None and self.combattant_j1 is not None:
            self.combattant_j2 = random.choice(self.j2.combattants_disponibles())

    # ------------------------------------------------------------ actions
    def soumettre_combattant(self, combattant_id):
        if self.phase != "choix_combattant":
            raise ErreurPartie("Ce n'est pas la phase de choix du Combattant")

        if self.j1 is self.joueur_humain:
            cible_joueur, attr = self.j1, "combattant_j1"
        else:
            if self.combattant_j1 is None:
                raise ErreurPartie("En attente du choix de Combattant de l'IA")
            cible_joueur, attr = self.j2, "combattant_j2"

        if getattr(self, attr) is not None:
            raise ErreurPartie("Le Combattant humain a deja ete choisi pour ce duel")

        instance = next((c for c in cible_joueur.combattants_disponibles() if c.template.id == combattant_id), None)
        if instance is None:
            raise ErreurPartie("Combattant indisponible")
        setattr(self, attr, instance)

        self._auto_choix_combattant_ia_si_necessaire()
        if self.combattant_j1 is not None and self.combattant_j2 is not None:
            self.phase = "choix_glyphe"
        return self.etat_dict()

    def soumettre_glyphe(self, glyphe_id):
        if self.phase != "choix_glyphe":
            raise ErreurPartie("Ce n'est pas la phase de choix du Glyphe")

        joueur_humain_est_j1 = self.j1 is self.joueur_humain
        glyphe_humain = self.joueur_humain.retirer_glyphe(glyphe_id)
        if glyphe_humain is None:
            raise ErreurPartie("Glyphe indisponible dans la main")
        glyphe_ia = random.choice(self.joueur_ia.main)
        self.joueur_ia.main.remove(glyphe_ia)

        glyphe_j1 = glyphe_humain if joueur_humain_est_j1 else glyphe_ia
        glyphe_j2 = glyphe_ia if joueur_humain_est_j1 else glyphe_humain

        resultat = resoudre_duel(
            self.j1, self.combattant_j1, glyphe_j1,
            self.j2, self.combattant_j2, glyphe_j2,
            self.duel_numero, NB_DUELS_MAX,
        )
        self.combattant_j1.utilise = True
        self.combattant_j2.utilise = True
        resultat["duel_numero"] = self.duel_numero
        resultat["combattant_j1"] = {"nom": self.combattant_j1.template.nom, "glyphe": glyphe_j1.notation_txt(), "role": "humain" if joueur_humain_est_j1 else "ia"}
        resultat["combattant_j2"] = {"nom": self.combattant_j2.template.nom, "glyphe": glyphe_j2.notation_txt(), "role": "ia" if joueur_humain_est_j1 else "humain"}
        self.dernier_resultat = resultat
        self.historique.append(resultat)
        self.phase = "duel_resolu"

        self._verifier_fin_partie(fin_de_manche=(self.duel_numero >= NB_DUELS_MAX))
        return self.etat_dict()

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
        self.dernier_resultat = None
        self.phase = "choix_combattant"
        self._auto_choix_combattant_ia_si_necessaire()
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

    # --------------------------------------------------------------- etat
    def etat_dict(self):
        return {
            "phase": self.phase,
            "duel_numero": self.duel_numero,
            "duels_max": NB_DUELS_MAX,
            "j1": "humain" if self.j1 is self.joueur_humain else "ia",
            "joueur_humain": self.joueur_humain.to_dict(),
            "joueur_ia": self.joueur_ia.to_dict(cacher_main=True),
            "combattant_j1": self.combattant_j1.template.id if self.combattant_j1 else None,
            "combattant_j2": self.combattant_j2.template.id if self.combattant_j2 else None,
            "dernier_resultat": self.dernier_resultat,
            "terminee": self.terminee,
            "vainqueur": self.vainqueur,
        }
