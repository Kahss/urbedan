"""Orchestration d'une Partie d'Urban Eredan : mise en place, tour de jeu, IA.

Version "draft de des". Chaque duel se deroule en trois temps :

1. **Tirage** : un pool central de 6 des est lance (deux rouges, deux bleus, deux
   violets). Le resultat est immediatement visible des deux joueurs.
2. **Choix des Combattants** : J1 engage son Combattant en voyant le pool, puis J2 engage
   le sien en voyant le pool et le Combattant de J1.
3. **Draft** : le Combattant de meilleure initiative choisit le premier (J1 en cas
   d'egalite), puis les joueurs prennent un de a tour de role jusqu'a en avoir 3 chacun.
   Le pool est donc integralement reparti.

La Puissance et l'Energie de chaque Combattant pour le duel sont la somme de celles de
ses 3 des draftes.
"""
import json
import random

from .des import DES_PAR_JOUEUR, lancer_pool
from .ia import choisir_combattant, choisir_de
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

        self.duel_numero = 1
        self.j1 = random.choice([self.joueur_humain, self.joueur_ia])
        self.j2 = self.joueur_ia if self.j1 is self.joueur_humain else self.joueur_humain
        self.dernier_resultat = None
        self.historique = []
        self.terminee = False
        self.vainqueur = None
        self._preparer_duel()

    # ------------------------------------------------------------ helpers
    def _joueur_du_role(self, role):
        return self.j1 if role == "j1" else self.j2

    def _combattant_du_role(self, role):
        return self.combattant_j1 if role == "j1" else self.combattant_j2

    def _draft_du_role(self, role):
        return self.draft_j1 if role == "j1" else self.draft_j2

    @staticmethod
    def _role_oppose(role):
        return "j2" if role == "j1" else "j1"

    def _role_humain(self):
        return "j1" if self.j1 is self.joueur_humain else "j2"

    # -------------------------------------------------------- mise en place
    def _preparer_duel(self):
        """Lance le pool central du duel et remet a zero l'etat de la manche."""
        self.pool_initial = lancer_pool()
        self.pool_des = list(self.pool_initial)
        self.combattant_j1 = None
        self.combattant_j2 = None
        self.draft_j1 = []
        self.draft_j2 = []
        self.drafteur_courant = None
        self.premier_drafteur = None
        self.dernier_resultat = None
        self.phase = "choix_combattant"
        self._auto_choix_ia_si_necessaire()

    # ------------------------------------------------------------------ IA
    def _auto_choix_ia_si_necessaire(self):
        if self.j1.est_ia and self.combattant_j1 is None:
            self._choix_ia(self.j1, "j1", "combattant_j1")
        if self.j2.est_ia and self.combattant_j2 is None and self.combattant_j1 is not None:
            self._choix_ia(self.j2, "j2", "combattant_j2")
        if self.combattant_j1 is not None and self.combattant_j2 is not None and self.phase == "choix_combattant":
            self._demarrer_draft()

    def _choix_ia(self, joueur, role, attr_combattant):
        """L'IA choisit son Combattant (cf. ia.py) en simulant le draft qui suivra sur le
        pool deja tire. Si elle joue en second, elle connait deja le Combattant adverse ;
        sinon elle moyenne sur ceux encore disponibles en face."""
        adversaire = self.joueur_ia if joueur is self.joueur_humain else self.joueur_humain
        combattant_adverse = self.combattant_j1 if role == "j2" else None
        instance = choisir_combattant(
            joueur, adversaire, combattant_adverse, role, self.pool_des,
            self.duel_numero, NB_DUELS_MAX, joueur.pv, adversaire.pv,
        )
        setattr(self, attr_combattant, instance)

    def _auto_draft_ia_si_necessaire(self):
        while self.phase == "draft" and self._joueur_du_role(self.drafteur_courant).est_ia:
            role = self.drafteur_courant
            de = choisir_de(
                self._combattant_du_role(role).template,
                self._draft_du_role(role),
                self._combattant_du_role(self._role_oppose(role)).template,
                self._draft_du_role(self._role_oppose(role)),
                self.pool_des, role, self.duel_numero, NB_DUELS_MAX,
                self._joueur_du_role(role).pv, self._joueur_du_role(self._role_oppose(role)).pv,
            )
            self._attribuer_de(role, de)

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
        return self.etat_dict()

    def _demarrer_draft(self):
        """Ouvre la phase de draft. Le Combattant a la meilleure initiative choisit en
        premier ; a egalite, c'est J1 (regle du spec)."""
        initiative_j1 = self.combattant_j1.template.initiative
        initiative_j2 = self.combattant_j2.template.initiative
        self.drafteur_courant = "j1" if initiative_j1 >= initiative_j2 else "j2"
        self.premier_drafteur = self.drafteur_courant
        self.phase = "draft"
        self._auto_draft_ia_si_necessaire()

    def drafter_de(self, de_id):
        if self.phase != "draft":
            raise ErreurPartie("Ce n'est pas la phase de draft")
        role_humain = self._role_humain()
        if self.drafteur_courant != role_humain:
            raise ErreurPartie("Ce n'est pas a toi de drafter")
        de = next((d for d in self.pool_des if d["id"] == de_id), None)
        if de is None:
            raise ErreurPartie("De indisponible dans le pool")

        self._attribuer_de(role_humain, de)
        return self.etat_dict()

    def _attribuer_de(self, role, de):
        """Retire `de` du pool central et l'ajoute a la main du role donne, puis passe la
        main a l'adversaire (alternance stricte) ou resout le duel si le draft est fini."""
        self.pool_des.remove(de)
        de["rang_draft"] = len(self.pool_initial) - len(self.pool_des)
        de["draft_par"] = role
        self._draft_du_role(role).append(de)

        if len(self.draft_j1) >= DES_PAR_JOUEUR and len(self.draft_j2) >= DES_PAR_JOUEUR:
            self._resoudre_duel_courant()
            return
        self.drafteur_courant = self._role_oppose(role)
        self._auto_draft_ia_si_necessaire()

    def _resoudre_duel_courant(self):
        joueur_humain_est_j1 = self.j1 is self.joueur_humain
        template_j1 = self.combattant_j1.template
        template_j2 = self.combattant_j2.template

        resultat = resoudre_duel(
            self.j1, self.combattant_j1, self.draft_j1,
            self.j2, self.combattant_j2, self.draft_j2,
            self.duel_numero, NB_DUELS_MAX,
        )
        self.combattant_j1.utilise = True
        self.combattant_j2.utilise = True
        resultat["duel_numero"] = self.duel_numero
        resultat["premier_drafteur"] = self.premier_drafteur
        resultat["combattant_j1"] = self._info_cote(
            template_j1, self.draft_j1, "humain" if joueur_humain_est_j1 else "ia"
        )
        resultat["combattant_j2"] = self._info_cote(
            template_j2, self.draft_j2, "ia" if joueur_humain_est_j1 else "humain"
        )
        self.dernier_resultat = resultat
        self.historique.append(resultat)
        self.phase = "duel_resolu"
        self.drafteur_courant = None

        self._verifier_fin_partie(fin_de_manche=(self.duel_numero >= NB_DUELS_MAX))

    @staticmethod
    def _info_cote(template, jet, role):
        return {
            "nom": template.nom,
            "role": role,
            "initiative": template.initiative,
            "jet": jet,
            "puissance_des": sum(de["puissance"] for de in jet),
            "energie": sum(de["energie"] for de in jet),
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
        self._preparer_duel()
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
            "des_par_joueur": DES_PAR_JOUEUR,
            "j1": "humain" if self.j1 is self.joueur_humain else "ia",
            "joueur_humain": self.joueur_humain.to_dict(),
            "joueur_ia": self.joueur_ia.to_dict(),
            "combattant_j1": self.combattant_j1.template.id if self.combattant_j1 else None,
            "combattant_j2": self.combattant_j2.template.id if self.combattant_j2 else None,
            "pool_des": self.pool_des,
            "pool_initial": self.pool_initial,
            "draft_j1": self.draft_j1,
            "draft_j2": self.draft_j2,
            "drafteur_courant": self.drafteur_courant,
            "premier_drafteur": self.premier_drafteur,
            "dernier_resultat": self.dernier_resultat,
            "terminee": self.terminee,
            "vainqueur": self.vainqueur,
        }
