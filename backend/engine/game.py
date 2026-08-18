"""Orchestration d'une Partie d'Urban Eredan : mise en place, duels, batailles, IA."""
import json
import random

from .batailles import Pioches
from .ia import choisir_combattant, choisir_pioche
from .models import CombattantEnEquipe, CombattantTemplate, Joueur

NB_DUELS_MAX = 4
PV_DEPART = 10
# Un duel est remporte par le premier Combattant a gagner 3 batailles.
BATAILLES_POUR_GAGNER = 3
# Les batailles nulles ne rapportent rien : sans plafond, deux Combattants aux
# caracteristiques identiques ne se separeraient jamais. Au-dela de 7 cartes revelees,
# c'est le nombre de batailles remportees qui tranche.
CARTES_MAX_PAR_DUEL = 7

ROLE_OPPOSE = {"j1": "j2", "j2": "j1"}


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

        # Les 2 pioches de cartes Bataille, remelangees au debut de chaque duel.
        self.pioches = Pioches()

        self.duel_numero = 1
        self.j1 = random.choice([self.joueur_humain, self.joueur_ia])
        self.j2 = self.joueur_ia if self.j1 is self.joueur_humain else self.joueur_humain
        self.historique = []
        self.dernier_resultat = None
        self.terminee = False
        self.vainqueur = None
        self._initialiser_duel()

    # ------------------------------------------------------------------ roles
    def _joueur(self, role):
        return self.j1 if role == "j1" else self.j2

    def _role_de(self, joueur):
        return "j1" if joueur is self.j1 else "j2"

    def _combattant(self, role):
        return self.combattant_j1 if role == "j1" else self.combattant_j2

    def _caracs(self, role):
        return self._combattant(role).template.caracs

    def _camp(self, role):
        """"humain" ou "ia" pour le joueur qui tient ce role dans le duel en cours."""
        return "humain" if self._joueur(role) is self.joueur_humain else "ia"

    # ------------------------------------------------------------------ duel
    def _initialiser_duel(self):
        # Le deck complet est remelange et recoupe en deux pioches : chaque duel repart du
        # meme ensemble de cartes, sans memoire du duel precedent.
        self.pioches.remelanger()
        self.combattant_j1 = None
        self.combattant_j2 = None
        self.batailles = {"j1": [], "j2": []}
        self.nulles = []
        self.journal_batailles = []
        # Les batailles se piochent en commencant par J1, puis a tour de role.
        self.role_actif = "j1"
        self.phase = "choix_combattant"
        self.dernier_resultat = None
        self._avancer()

    def _avancer(self):
        """Fait jouer l'IA tant que c'est a elle d'agir, et rend la main des qu'une
        decision revient au joueur humain (ou que le duel est resolu)."""
        while True:
            if self.phase == "choix_combattant":
                if self.combattant_j1 is None:
                    if not self.j1.est_ia:
                        return
                    self.combattant_j1 = choisir_combattant(self.j1)
                    continue
                if self.combattant_j2 is None:
                    if not self.j2.est_ia:
                        return
                    self.combattant_j2 = choisir_combattant(self.j2)
                    continue
                self.phase = "batailles"
                continue

            if self.phase == "batailles":
                if not self._joueur(self.role_actif).est_ia:
                    return
                role = self.role_actif
                index = choisir_pioche(
                    self.pioches.sommets(),
                    self.pioches.cartes_en_pioche(),
                    self._caracs(role),
                    self._caracs(ROLE_OPPOSE[role]),
                    role,
                )
                self._jouer_bataille(index)
                continue

            return

    # --------------------------------------------------------------- actions
    def soumettre_combattant(self, combattant_id):
        """Engage le Combattant du joueur humain. J1 engage d'abord, face visible ; J2
        choisit ensuite en connaissant l'adversaire qu'il affronte."""
        if self.phase != "choix_combattant":
            raise ErreurPartie("Ce n'est pas la phase de choix du Combattant")

        role = self._role_de(self.joueur_humain)
        if self._combattant(role) is not None:
            raise ErreurPartie("Le Combattant humain a deja ete choisi pour ce duel")
        if role == "j2" and self.combattant_j1 is None:
            raise ErreurPartie("En attente du choix de Combattant de l'IA")

        instance = next(
            (c for c in self.joueur_humain.combattants_disponibles() if c.template.id == combattant_id),
            None,
        )
        if instance is None:
            raise ErreurPartie("Combattant indisponible")

        if role == "j1":
            self.combattant_j1 = instance
        else:
            self.combattant_j2 = instance

        self._avancer()
        return self.etat_dict()

    def soumettre_pioche(self, index):
        """Le joueur humain choisit l'une des 2 pioches de cartes Bataille."""
        if self.phase != "batailles":
            raise ErreurPartie("Ce n'est pas la phase de resolution des batailles")
        if self._joueur(self.role_actif) is not self.joueur_humain:
            raise ErreurPartie("Ce n'est pas a toi de piocher")
        if index not in (0, 1):
            raise ErreurPartie("Pioche inconnue")

        self._jouer_bataille(index)
        self._avancer()
        return self.etat_dict()

    # -------------------------------------------------------------- batailles
    def _jouer_bataille(self, index):
        """Revele la carte du dessus de la pioche choisie, resout sa condition et
        l'attribue au vainqueur ; si la bataille est nulle, la carte est ecartee."""
        role_choix = self.role_actif
        carte = self.pioches.piocher(index)
        gagnant_role = carte.resoudre(self._caracs("j1"), self._caracs("j2"))

        if gagnant_role is None:
            self.nulles.append(carte)
        else:
            self.batailles[gagnant_role].append(carte)

        self.journal_batailles.append({
            "numero": len(self.journal_batailles) + 1,
            "pioche": index + 1,
            "choisie_par": self._camp(role_choix),
            "carte": carte.to_dict(revele=True),
            "valeurs": {
                "j1": carte.detail(self._caracs("j1")),
                "j2": carte.detail(self._caracs("j2")),
            },
            "gagnant_role": gagnant_role,
            "gagnant_camp": self._camp(gagnant_role) if gagnant_role else None,
            "gagnant_nom": self._combattant(gagnant_role).template.nom if gagnant_role else None,
            "score": self._score(),
        })

        if self._duel_termine():
            self._conclure_duel()
        else:
            self.role_actif = ROLE_OPPOSE[role_choix]

    def _score(self):
        return {"j1": len(self.batailles["j1"]), "j2": len(self.batailles["j2"])}

    def _cartes_revelees(self):
        return len(self.journal_batailles)

    def _duel_termine(self):
        score = self._score()
        return (
            max(score.values()) >= BATAILLES_POUR_GAGNER
            or self._cartes_revelees() >= CARTES_MAX_PAR_DUEL
        )

    def _conclure_duel(self):
        """Designe le vainqueur du duel, applique ses Degats et archive le resultat."""
        score = self._score()
        if score["j1"] > score["j2"]:
            gagnants_roles = ["j1"]
        elif score["j2"] > score["j1"]:
            gagnants_roles = ["j2"]
        else:
            # Plafond de cartes atteint sans qu'un camp prenne l'avantage : double
            # victoire, les deux Combattants infligent leurs Degats (cf. game.md).
            gagnants_roles = ["j1", "j2"]

        par_plafond = max(score.values()) < BATAILLES_POUR_GAGNER

        log = []
        for entree in self.journal_batailles:
            carte = entree["carte"]
            valeurs = " contre ".join(
                f"{self._combattant(role).template.nom} "
                + "/".join(str(valeur) for _, valeur in entree["valeurs"][role])
                for role in ("j1", "j2")
            )
            issue = (
                f"{entree['gagnant_nom']} remporte la bataille"
                if entree["gagnant_nom"]
                else "bataille nulle"
            )
            log.append(
                f"Bataille {entree['numero']} - {carte['nom']} ({carte['condition']}) : "
                f"{valeurs} -> {issue}"
            )

        if par_plafond:
            log.append(
                f"{CARTES_MAX_PAR_DUEL} cartes revelees sans 3 batailles : "
                f"le score ({score['j1']}-{score['j2']}) tranche le duel"
            )

        degats = {}
        for role in gagnants_roles:
            combattant = self._combattant(role)
            adversaire = self._joueur(ROLE_OPPOSE[role])
            adversaire.pv -= combattant.template.degats
            degats[combattant.template.nom] = combattant.template.degats
            log.append(
                f"{combattant.template.nom} remporte le duel {score[role]}-{score[ROLE_OPPOSE[role]]} "
                f"et inflige {combattant.template.degats} Degats"
            )
        if len(gagnants_roles) == 2:
            log.insert(-2, "Double victoire : les deux Combattants infligent leurs Degats")

        self.combattant_j1.utilise = True
        self.combattant_j2.utilise = True

        resultat = {
            "duel_numero": self.duel_numero,
            "score": score,
            "nulles": len(self.nulles),
            "cartes_revelees": self._cartes_revelees(),
            "par_plafond": par_plafond,
            "gagnants_roles": gagnants_roles,
            "gagnants_ids": [self._combattant(role).template.id for role in gagnants_roles],
            "gagnants": [self._combattant(role).template.nom for role in gagnants_roles],
            "degats": degats,
            "journal_batailles": list(self.journal_batailles),
            "log": log,
        }
        for role in ("j1", "j2"):
            combattant = self._combattant(role)
            resultat["combattant_" + role] = {
                "id": combattant.template.id,
                "nom": combattant.template.nom,
                "camp": self._camp(role),
                "batailles": score[role],
                "degats": combattant.template.degats,
            }

        self.dernier_resultat = resultat
        self.historique.append(resultat)
        self.phase = "duel_resolu"
        self._verifier_fin_partie(fin_de_manche=(self.duel_numero >= NB_DUELS_MAX))

    def duel_suivant(self):
        if self.phase != "duel_resolu":
            raise ErreurPartie("Le duel courant n'est pas termine")
        if self.terminee:
            return self.etat_dict()

        # Le premier joueur du duel suivant est le gagnant du duel precedent ; en cas de
        # double victoire, J1 et J2 echangent leurs roles.
        gagnants_roles = self.dernier_resultat["gagnants_roles"]
        if len(gagnants_roles) == 2 or gagnants_roles[0] == "j2":
            self.j1, self.j2 = self.j2, self.j1

        self.duel_numero += 1
        self._initialiser_duel()
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
        sommets = self.pioches.sommets()
        return {
            "phase": self.phase,
            "duel_numero": self.duel_numero,
            "duels_max": NB_DUELS_MAX,
            "batailles_pour_gagner": BATAILLES_POUR_GAGNER,
            "cartes_max_par_duel": CARTES_MAX_PAR_DUEL,
            "j1": self._camp("j1"),
            "joueur_humain": self.joueur_humain.to_dict(),
            "joueur_ia": self.joueur_ia.to_dict(),
            "combattant_j1": self.combattant_j1.template.id if self.combattant_j1 else None,
            "combattant_j2": self.combattant_j2.template.id if self.combattant_j2 else None,
            "role_actif": self.role_actif if self.phase == "batailles" else None,
            "joueur_actif": self._camp(self.role_actif) if self.phase == "batailles" else None,
            "score": self._score(),
            "cartes_revelees": self._cartes_revelees(),
            "journal_batailles": self.journal_batailles,
            "pioches": [
                {
                    "index": index,
                    "verso": sommet.verso if sommet else None,
                    "restantes": len(self.pioches.piles[index]),
                }
                for index, sommet in enumerate(sommets)
            ],
            "dernier_resultat": self.dernier_resultat,
            "terminee": self.terminee,
            "vainqueur": self.vainqueur,
        }
