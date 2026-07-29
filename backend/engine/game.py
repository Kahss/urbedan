"""Orchestration d'une Partie d'Urban Eredan : mise en place, tour de jeu, IA."""
import json
import random
from collections import Counter

from .ia import choisir_combattant_et_glyphe
from .models import GLYPH_DISTRIBUTION, CombattantEnEquipe, CombattantTemplate, Joueur, construire_deck_glyphes
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

        self.deck_glyphes = construire_deck_glyphes()

        self.duel_numero = 1
        self.j1 = None
        self.j2 = None
        self.combattant_j1 = None
        self.combattant_j2 = None
        self.glyphe_j1 = None
        self.glyphe_j2 = None
        self.phase = "choix_combattant"
        self.dernier_resultat = None
        self.historique = []
        self.terminee = False
        self.vainqueur = None

        self.j1 = random.choice([self.joueur_humain, self.joueur_ia])
        self.j2 = self.joueur_ia if self.j1 is self.joueur_humain else self.joueur_humain
        self._distribuer_main_initiale()
        self._piocher_glyphes_manche()
        self._auto_choix_ia_si_necessaire()

    # ------------------------------------------------------------------ IA
    def _auto_choix_ia_si_necessaire(self):
        if self.j1.est_ia and self.combattant_j1 is None:
            self._choix_ia(self.j1, "j1", "combattant_j1", "glyphe_j1")
        if self.j2.est_ia and self.combattant_j2 is None and self.combattant_j1 is not None:
            self._choix_ia(self.j2, "j2", "combattant_j2", "glyphe_j2")

    def _choix_ia(self, joueur, role, attr_combattant, attr_glyphe):
        """L'IA choisit, via une heuristique simple (cf. ia.py), le Combattant et le
        Glyphe de sa main qui maximisent la Puissance totale estimee pour ce duel."""
        adversaire = self.joueur_ia if joueur is self.joueur_humain else self.joueur_humain
        instance, glyphe = choisir_combattant_et_glyphe(
            joueur, role, self.duel_numero, NB_DUELS_MAX, joueur.pv, adversaire.pv
        )
        joueur.main_glyphes.remove(glyphe)
        setattr(self, attr_combattant, instance)
        setattr(self, attr_glyphe, glyphe)

    # ---------------------------------------------------------------- pioche
    def _distribuer_main_initiale(self):
        """A la mise en place de la partie, chaque joueur recoit un premier Glyphe en
        main (avant meme la pioche de la premiere manche)."""
        self.joueur_humain.main_glyphes.append(self.deck_glyphes.pop())
        self.joueur_ia.main_glyphes.append(self.deck_glyphes.pop())

    def _piocher_glyphes_manche(self):
        """Au debut de chaque manche, chaque joueur pioche un Glyphe supplementaire
        dans le deck commun, qui s'ajoute a celui deja en main (non joue lors de la
        manche precedente) : il choisira lequel des deux jouer sur son Combattant."""
        self.joueur_humain.main_glyphes.append(self.deck_glyphes.pop())
        self.joueur_ia.main_glyphes.append(self.deck_glyphes.pop())

    # ------------------------------------------------------------ actions
    def soumettre_combattant(self, combattant_id, glyphe_id):
        if self.phase != "choix_combattant":
            raise ErreurPartie("Ce n'est pas la phase de choix du Combattant")

        if self.j1 is self.joueur_humain:
            cible_joueur, attr_combattant, attr_glyphe = self.j1, "combattant_j1", "glyphe_j1"
        else:
            if self.combattant_j1 is None:
                raise ErreurPartie("En attente du choix de Combattant de l'IA")
            cible_joueur, attr_combattant, attr_glyphe = self.j2, "combattant_j2", "glyphe_j2"

        if getattr(self, attr_combattant) is not None:
            raise ErreurPartie("Le Combattant humain a deja ete choisi pour ce duel")

        instance = next((c for c in cible_joueur.combattants_disponibles() if c.template.id == combattant_id), None)
        if instance is None:
            raise ErreurPartie("Combattant indisponible")

        glyphe = next((g for g in cible_joueur.main_glyphes if g.id == glyphe_id), None)
        if glyphe is None:
            raise ErreurPartie("Glyphe indisponible dans la main du joueur")

        cible_joueur.main_glyphes.remove(glyphe)
        setattr(self, attr_combattant, instance)
        setattr(self, attr_glyphe, glyphe)

        self._auto_choix_ia_si_necessaire()
        if self.combattant_j1 is not None and self.combattant_j2 is not None:
            self._resoudre_duel_courant()
        return self.etat_dict()

    def _resoudre_duel_courant(self):
        joueur_humain_est_j1 = self.j1 is self.joueur_humain
        glyphe_j1 = self.glyphe_j1
        glyphe_j2 = self.glyphe_j2

        resultat = resoudre_duel(
            self.j1, self.combattant_j1, glyphe_j1,
            self.j2, self.combattant_j2, glyphe_j2,
            self.duel_numero, NB_DUELS_MAX,
        )
        self.combattant_j1.utilise = True
        self.combattant_j2.utilise = True
        resultat["duel_numero"] = self.duel_numero
        resultat["combattant_j1"] = {"nom": self.combattant_j1.template.nom, "glyphe": glyphe_j1.notation_txt(), "puissance_glyphe": glyphe_j1.puissance, "energie": glyphe_j1.energie, "role": "humain" if joueur_humain_est_j1 else "ia"}
        resultat["combattant_j2"] = {"nom": self.combattant_j2.template.nom, "glyphe": glyphe_j2.notation_txt(), "puissance_glyphe": glyphe_j2.puissance, "energie": glyphe_j2.energie, "role": "ia" if joueur_humain_est_j1 else "humain"}
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
        self.glyphe_j1 = None
        self.glyphe_j2 = None
        self.dernier_resultat = None
        self.phase = "choix_combattant"
        self._piocher_glyphes_manche()
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

    # --------------------------------------------------------- comptage Glyphes
    def glyphes_restants(self):
        """Pour chacun des 4 types de Glyphe, combien d'exemplaires restent
        potentiellement disponibles (sur le total de depart), etant donne ceux deja
        joues (reveles en resolution de duel). Les Glyphes actuellement en main (y
        compris la main cachee de l'IA) comptent donc comme "restants", puisque leur
        type n'est pas encore connu de l'autre joueur avant d'etre joue."""
        joues = Counter()
        for resultat in self.historique:
            for cle in ("combattant_j1", "combattant_j2"):
                info = resultat[cle]
                joues[(info["puissance_glyphe"], info["energie"])] += 1
        return [
            {
                "puissance": puissance,
                "energie": energie,
                "total": total,
                "joues": joues.get((puissance, energie), 0),
                "restants": total - joues.get((puissance, energie), 0),
            }
            for puissance, energie, total in GLYPH_DISTRIBUTION
        ]

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
            "glyphes_restants": self.glyphes_restants(),
            "terminee": self.terminee,
            "vainqueur": self.vainqueur,
        }
