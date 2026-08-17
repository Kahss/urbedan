"""Orchestration d'une Partie d'Urban Eredan : mise en place, tour de jeu, IA."""
import json
import random

from .champs import construire_deck
from .ia import choisir_combattant
from .models import CombattantEnEquipe, CombattantTemplate, Joueur
from .powers import resoudre_duel

NB_DUELS_MAX = 4
PV_DEPART = 10


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

        equipe_ia_ids = random.sample([cid for cid in templates_par_id if cid not in equipe_joueur_ids], 4)

        self.joueur_humain = Joueur(
            "humain", False, [CombattantEnEquipe(templates_par_id[cid]) for cid in equipe_joueur_ids]
        )
        self.joueur_ia = Joueur(
            "ia", True, [CombattantEnEquipe(templates_par_id[cid]) for cid in equipe_ia_ids]
        )
        self.joueur_humain.pv = PV_DEPART
        self.joueur_ia.pv = PV_DEPART

        self.deck_champs = construire_deck()

        self.duel_numero = 1
        self.j1 = None
        self.j2 = None
        self.combattant_j1 = None
        self.combattant_j2 = None
        self.champ = None
        self.phase = "choix_combattant"
        self.dernier_resultat = None
        self.historique = []
        self.terminee = False
        self.vainqueur = None

        self.j1 = random.choice([self.joueur_humain, self.joueur_ia])
        self.j2 = self.joueur_ia if self.j1 is self.joueur_humain else self.joueur_humain
        self._reveler_champ()
        self._auto_choix_ia_si_necessaire()

    # ------------------------------------------------------------ champ de bataille
    def _reveler_champ(self):
        """Retourne le dos du champ de bataille du duel : les joueurs decouvrent la
        couleur des 3 cases, et seulement elle, avant d'engager leur Combattant."""
        self.champ = self.deck_champs.pop()

    def _adversaire_de(self, joueur):
        return self.joueur_ia if joueur is self.joueur_humain else self.joueur_humain

    # ------------------------------------------------------------------ IA
    def _auto_choix_ia_si_necessaire(self):
        if self.j1.est_ia and self.combattant_j1 is None:
            self._choix_ia(self.j1, "j1")
        if self.j2.est_ia and self.combattant_j2 is None and self.combattant_j1 is not None:
            self._choix_ia(self.j2, "j2")

    def _choix_ia(self, joueur, role):
        """L'IA choisit son Combattant a partir du seul dos du champ de bataille (cf.
        ia.py) : en J2 elle connait le Combattant deja engage par J1, en J1 non."""
        instance = choisir_combattant(
            joueur,
            self._adversaire_de(joueur),
            role,
            self.duel_numero,
            NB_DUELS_MAX,
            self.champ.dos(),
            self.combattant_j1 if role == "j2" else None,
        )
        setattr(self, "combattant_" + role, instance)

    # ------------------------------------------------------------ actions
    def soumettre_combattant(self, combattant_id):
        if self.phase != "choix_combattant":
            raise ErreurPartie("Ce n'est pas la phase de choix du Combattant")

        if self.j1 is self.joueur_humain:
            role = "j1"
        else:
            if self.combattant_j1 is None:
                raise ErreurPartie("En attente du choix de Combattant de l'IA")
            role = "j2"

        if getattr(self, "combattant_" + role) is not None:
            raise ErreurPartie("Le Combattant humain a deja ete choisi pour ce duel")

        instance = next(
            (c for c in self.joueur_humain.combattants_disponibles() if c.template.id == combattant_id), None
        )
        if instance is None:
            raise ErreurPartie("Combattant indisponible")

        setattr(self, "combattant_" + role, instance)

        self._auto_choix_ia_si_necessaire()
        if self.combattant_j1 is not None and self.combattant_j2 is not None:
            self._resoudre_duel_courant()
        return self.etat_dict()

    def _info_cote(self, instance, role_joueur):
        """Ce que le champ de bataille a rapporte a ce Combattant, une fois revele."""
        template = instance.template
        return {
            "nom": template.nom,
            "role": role_joueur,
            "avantage": template.avantage,
            "bonus_champ": self.champ.bonus(template.avantage),
        }

    def _resoudre_duel_courant(self):
        joueur_humain_est_j1 = self.j1 is self.joueur_humain

        resultat = resoudre_duel(
            self.j1, self.combattant_j1,
            self.j2, self.combattant_j2,
            self.champ, self.duel_numero, NB_DUELS_MAX,
        )
        self.combattant_j1.utilise = True
        self.combattant_j2.utilise = True
        resultat["duel_numero"] = self.duel_numero
        resultat["champ"] = self.champ.to_dict(revele=True)
        resultat["combattant_j1"] = self._info_cote(
            self.combattant_j1, "humain" if joueur_humain_est_j1 else "ia"
        )
        resultat["combattant_j2"] = self._info_cote(
            self.combattant_j2, "ia" if joueur_humain_est_j1 else "humain"
        )
        self.dernier_resultat = resultat
        self.historique.append(resultat)
        self.phase = "duel_resolu"

        self._verifier_fin_partie(fin_de_manche=(self.duel_numero >= NB_DUELS_MAX))

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
        self._reveler_champ()
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

    # --------------------------------------------------------------- etat
    def etat_dict(self):
        # Le recto du champ de bataille n'est serialise qu'une fois le duel resolu : tant
        # que la phase de choix dure, l'API elle-meme ne transmet que le dos.
        return {
            "phase": self.phase,
            "duel_numero": self.duel_numero,
            "duels_max": NB_DUELS_MAX,
            "j1": "humain" if self.j1 is self.joueur_humain else "ia",
            "joueur_humain": self.joueur_humain.to_dict(),
            "joueur_ia": self.joueur_ia.to_dict(),
            "combattant_j1": self.combattant_j1.template.id if self.combattant_j1 else None,
            "combattant_j2": self.combattant_j2.template.id if self.combattant_j2 else None,
            "champ": self.champ.to_dict(revele=(self.phase == "duel_resolu")),
            "dernier_resultat": self.dernier_resultat,
            "terminee": self.terminee,
            "vainqueur": self.vainqueur,
        }
