"""Orchestration d'une Partie d'Urban Eredan, version duo (voir versions/duo.md).

Une partie est une serie de NB_BATAILLES_MAX batailles. A chaque bataille :
1. La carte bataille du tour est revelee (information publique, elle fixe l'enjeu).
2. Les deux joueurs choisissent SIMULTANEMENT le duo de 2 Combattants qu'ils engagent.
   L'IA verrouille donc son duo avant de connaitre celui du joueur humain, sauf lorsqu'une
   carte Reperage / Intimidation gagnee au tour precedent inverse cet ordre.
3. Les deux duos sont reveles.
4. Chaque joueur designe la cible des effets a cible unique de ses Pouvoirs.
5. Les Pouvoirs sont resolus, les sommes de Puissance comparees, les Degats appliques.
6. Le ou les vainqueurs appliquent l'effet de la carte bataille.
"""
import json
import random

from .batailles import REVELATIONS, bonus_degats, construire_deck_batailles
from .ia import choisir_ciblages, choisir_duo, estimer_puissance_duo_adverse
from .models import (
    MAX_UTILISATIONS,
    PV_DEPART,
    TAILLE_DUO,
    TAILLE_EQUIPE,
    CombattantEnEquipe,
    CombattantTemplate,
    Joueur,
)
from .powers import CampBataille, pouvoir_requiert_cible, resoudre_bataille

NB_BATAILLES_MAX = 4

PHASE_CHOIX_DUO = "choix_duo"
PHASE_CIBLAGE = "ciblage"
PHASE_BATAILLE_RESOLUE = "bataille_resolue"


class ErreurPartie(Exception):
    pass


def charger_combattants(chemin_json):
    with open(chemin_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {c["id"]: CombattantTemplate(c) for c in data["combattants"]}


class Partie:
    def __init__(self, templates_par_id, equipe_joueur_ids):
        if len(equipe_joueur_ids) != TAILLE_EQUIPE or len(set(equipe_joueur_ids)) != TAILLE_EQUIPE:
            raise ErreurPartie(
                f"L'equipe du joueur doit comporter {TAILLE_EQUIPE} Combattants distincts"
            )
        for cid in equipe_joueur_ids:
            if cid not in templates_par_id:
                raise ErreurPartie(f"Combattant inconnu : {cid}")

        restants = [cid for cid in templates_par_id if cid not in equipe_joueur_ids]
        if len(restants) < TAILLE_EQUIPE:
            raise ErreurPartie("Pas assez de Combattants disponibles pour constituer l'equipe de l'IA")
        equipe_ia_ids = random.sample(restants, TAILLE_EQUIPE)

        self.joueur_humain = Joueur(
            "humain", False, [CombattantEnEquipe(templates_par_id[cid]) for cid in equipe_joueur_ids]
        )
        self.joueur_ia = Joueur(
            "ia", True, [CombattantEnEquipe(templates_par_id[cid]) for cid in equipe_ia_ids]
        )

        self.deck_batailles = construire_deck_batailles()
        self.tour = 1
        self.j1 = random.choice([self.joueur_humain, self.joueur_ia])
        self.j2 = self.joueur_ia if self.j1 is self.joueur_humain else self.joueur_humain

        # {nom du joueur qui doit reveler: nombre de Combattants a reveler}, alimente par
        # les cartes bataille Reperage / Intimidation gagnees a la bataille precedente.
        self.revelation_due = {}
        self.revelation_courante = {}

        self.carte_bataille = None
        self.duo_humain = None
        self.duo_ia = None
        self.reveles_ia = []  # Combattants du duo de l'IA reveles au joueur humain
        self.camp_humain = None
        self.camp_ia = None
        self.dernier_resultat = None
        self.historique = []
        self.phase = PHASE_CHOIX_DUO
        self.terminee = False
        self.vainqueur = None

        self._preparer_bataille()

    # ------------------------------------------------------------- helpers
    def batailles_restantes(self):
        return NB_BATAILLES_MAX - self.tour + 1

    def role_de(self, joueur):
        return "J1" if joueur is self.j1 else "J2"

    def _adversaire(self, joueur):
        return self.joueur_ia if joueur is self.joueur_humain else self.joueur_humain

    def _duo(self, joueur):
        return self.duo_humain if joueur is self.joueur_humain else self.duo_ia

    def _duos_legaux(self, joueur):
        return joueur.duos_legaux(self.batailles_restantes())

    # -------------------------------------------------- preparation du tour
    def _preparer_bataille(self):
        self.carte_bataille = self.deck_batailles.pop()
        self.revelation_courante = self.revelation_due
        self.revelation_due = {}
        self.duo_humain = None
        self.duo_ia = None
        self.reveles_ia = []
        self.camp_humain = None
        self.camp_ia = None
        self.dernier_resultat = None
        self.phase = PHASE_CHOIX_DUO

        ia_doit_reveler = "ia" in self.revelation_courante
        humain_doit_reveler = "humain" in self.revelation_courante

        # L'IA verrouille son duo des l'ouverture de la bataille (donc a l'aveugle, ce qui
        # garantit la simultaneite du choix), sauf lorsque c'est au joueur humain de
        # reveler : dans ce cas seulement, l'IA attend de connaitre une partie de son duo.
        # Si les deux doivent reveler (double victoire sur une carte d'information), l'IA
        # choisit malgre tout a l'aveugle : son devoir de revelation est deja rempli par le
        # fait qu'elle s'engage sans rien savoir.
        if not (humain_doit_reveler and not ia_doit_reveler):
            self.duo_ia = self._choix_ia_duo(puissance_adverse_estimee=None)
            if ia_doit_reveler:
                self.reveles_ia = random.sample(
                    list(self.duo_ia), min(self.revelation_courante["ia"], TAILLE_DUO)
                )

    def _choix_ia_duo(self, puissance_adverse_estimee):
        return choisir_duo(
            self.joueur_ia,
            self.role_de(self.joueur_ia),
            self.tour,
            NB_BATAILLES_MAX,
            self.joueur_ia.pv,
            self.joueur_humain.pv,
            self.batailles_restantes(),
            puissance_adverse_estimee=puissance_adverse_estimee,
        )

    # ------------------------------------------------------------- actions
    def soumettre_duo(self, combattant_ids):
        if self.phase != PHASE_CHOIX_DUO:
            raise ErreurPartie("Ce n'est pas la phase de choix du duo")
        if self.duo_humain is not None:
            raise ErreurPartie("Le duo du joueur a deja ete verrouille pour cette bataille")
        if not isinstance(combattant_ids, (list, tuple)) or len(set(combattant_ids)) != TAILLE_DUO:
            raise ErreurPartie(f"Un duo doit comporter {TAILLE_DUO} Combattants distincts")

        instances = []
        for cid in combattant_ids:
            instance = next(
                (c for c in self.joueur_humain.equipe if c.template.id == cid), None
            )
            if instance is None:
                raise ErreurPartie(f"Combattant absent de ton equipe : {cid}")
            if not instance.disponible():
                raise ErreurPartie(f"{instance.template.nom} a epuise ses {MAX_UTILISATIONS} utilisations")
            instances.append(instance)

        legaux = self._duos_legaux(self.joueur_humain)
        if not any(set(duo) == set(instances) for duo in legaux):
            raise ErreurPartie(
                "Ce duo rendrait une bataille suivante injouable (il ne resterait pas "
                "2 Combattants distincts a engager)"
            )

        self.duo_humain = tuple(instances)

        if self.duo_ia is None:
            # Le joueur humain devait reveler : l'IA choisit maintenant, en connaissant
            # une partie de son duo.
            nb = self.revelation_courante.get("humain", 0)
            reveles = random.sample(list(self.duo_humain), min(nb, TAILLE_DUO))
            self.duo_ia = self._choix_ia_duo(
                puissance_adverse_estimee=estimer_puissance_duo_adverse(
                    self.joueur_humain, reveles
                )
            )

        return self._reveler_et_cibler()

    def _reveler_et_cibler(self):
        """Construit les deux camps a partir des duos verrouilles, puis passe soit a la
        phase de ciblage (si au moins un Pouvoir du joueur humain requiert une cible),
        soit directement a la resolution."""
        self.camp_humain = self._construire_camp(self.joueur_humain)
        self.camp_ia = self._construire_camp(self.joueur_ia)
        self.camp_humain.adversaire = self.camp_ia
        self.camp_ia.adversaire = self.camp_humain

        if self.ciblages_requis():
            self.phase = PHASE_CIBLAGE
            return self.etat_dict()
        return self._resoudre()

    def _construire_camp(self, joueur):
        engagements = [(inst, inst.utilisations + 1) for inst in self._duo(joueur)]
        return CampBataille(joueur, engagements, self.role_de(joueur))

    def ciblages_requis(self):
        """Combattants du duo humain dont le Pouvoir exige de designer l'un des 2
        Combattants adverses."""
        if self.camp_humain is None:
            return []
        return [c for c in self.camp_humain.combattants if pouvoir_requiert_cible(c.pouvoir())]

    def soumettre_ciblages(self, ciblages):
        if self.phase != PHASE_CIBLAGE:
            raise ErreurPartie("Ce n'est pas la phase de ciblage")
        ciblages = ciblages or {}
        adverses = {c.template.id: c for c in self.camp_ia.combattants}
        for combattant in self.ciblages_requis():
            cible_id = ciblages.get(combattant.template.id)
            if cible_id not in adverses:
                raise ErreurPartie(
                    f"{combattant.template.nom} doit cibler l'un des 2 Combattants adverses"
                )
            combattant.cible = adverses[cible_id]
        return self._resoudre()

    # ---------------------------------------------------------- resolution
    def _resoudre(self):
        # L'IA designe ses propres cibles, une fois les deux duos connus.
        camps = {"humain": self.camp_humain, "ia": self.camp_ia}
        for combattant_id, cible_id in choisir_ciblages(
            self.camp_ia, self.tour, NB_BATAILLES_MAX
        ).items():
            source = next(c for c in self.camp_ia.combattants if c.template.id == combattant_id)
            source.cible = next(
                c for c in self.camp_humain.combattants if c.template.id == cible_id
            )

        camp_j1 = camps[self.j1.nom]
        camp_j2 = camps[self.j2.nom]
        resultat = resoudre_bataille(
            camp_j1, camp_j2, self.tour, NB_BATAILLES_MAX, bonus_degats(self.carte_bataille)
        )

        for camp in (self.camp_humain, self.camp_ia):
            for combattant in camp.combattants:
                combattant.instance.utilisations += 1

        self._appliquer_carte_bataille(resultat)

        resultat["tour"] = self.tour
        resultat["carte_bataille"] = dict(self.carte_bataille)
        resultat["j1"] = self.j1.nom
        resultat["pv"] = {"humain": self.joueur_humain.pv, "ia": self.joueur_ia.pv}
        self.dernier_resultat = resultat
        self.historique.append(resultat)
        self.phase = PHASE_BATAILLE_RESOLUE

        self._verifier_fin_partie(derniere_bataille=(self.tour >= NB_BATAILLES_MAX))
        return self.etat_dict()

    def _appliquer_carte_bataille(self, resultat):
        """Applique l'effet de la carte bataille du tour, par chaque camp vainqueur. Le
        bonus de Degats (Acharnement) a deja ete applique pendant la resolution."""
        effet = self.carte_bataille["effet"]
        nom_carte = self.carte_bataille["nom"]
        log = resultat["log"]

        for camp in (self.camp_humain, self.camp_ia):
            if not camp.gagnant:
                continue
            joueur = camp.joueur
            if effet == "butin":
                from .batailles import BONUS_BUTIN

                joueur.pv += BONUS_BUTIN
                log.append(f"{nom_carte} : {joueur.nom} gagne {BONUS_BUTIN} PV ({joueur.pv} PV)")
            elif effet == "second_souffle":
                noms = []
                for combattant in camp.combattants:
                    combattant.instance.utilisations = max(0, combattant.instance.utilisations - 1)
                    noms.append(combattant.template.nom)
                log.append(
                    f"{nom_carte} : {' et '.join(noms)} recuperent l'utilisation depensee "
                    f"pour cette bataille"
                )
            elif effet == "ovation":
                from .batailles import BONUS_OVATION_PAR_COMBATTANT

                premieres = [c for c in camp.combattants if c.n_utilisation == 1]
                gain = BONUS_OVATION_PAR_COMBATTANT * len(premieres)
                if gain:
                    joueur.pv += gain
                    log.append(
                        f"{nom_carte} : {joueur.nom} gagne {gain} PV "
                        f"({len(premieres)} Combattant(s) engage(s) pour la premiere fois) "
                        f"({joueur.pv} PV)"
                    )
                else:
                    log.append(
                        f"{nom_carte} : aucun Combattant du duo de {joueur.nom} n'etait "
                        "engage pour la premiere fois, aucun PV gagne"
                    )
            elif effet in REVELATIONS:
                adversaire = self._adversaire(joueur)
                self.revelation_due[adversaire.nom] = REVELATIONS[effet]
                log.append(
                    f"{nom_carte} : a la prochaine bataille, {adversaire.nom} verrouille "
                    f"son duo en premier et en revele {REVELATIONS[effet]} Combattant(s)"
                )

    def _verifier_fin_partie(self, derniere_bataille):
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
        elif derniere_bataille:
            self.terminee = True
            if pv_h > pv_i:
                self.vainqueur = "humain"
            elif pv_i > pv_h:
                self.vainqueur = "ia"
            else:
                self.vainqueur = None

    def bataille_suivante(self):
        if self.phase != PHASE_BATAILLE_RESOLUE:
            raise ErreurPartie("La bataille courante n'est pas terminee")
        if self.terminee:
            return self.etat_dict()

        gagnants = self.dernier_resultat["gagnants"]
        if len(gagnants) == 2:
            # Double victoire : J2 devient J1 et inversement (cf. game.md).
            self.j1, self.j2 = self.j2, self.j1
        else:
            self.j1 = self.joueur_humain if gagnants[0] == "humain" else self.joueur_ia
            self.j2 = self._adversaire(self.j1)

        self.tour += 1
        self._preparer_bataille()
        return self.etat_dict()

    # --------------------------------------------------------------- etat
    def _duo_ids(self, joueur):
        duo = self._duo(joueur)
        return [inst.template.id for inst in duo] if duo else None

    def etat_dict(self):
        duo_ia_visible = self.phase != PHASE_CHOIX_DUO
        return {
            "phase": self.phase,
            "tour": self.tour,
            "tours_max": NB_BATAILLES_MAX,
            "batailles_restantes": self.batailles_restantes(),
            "j1": self.j1.nom,
            "carte_bataille": dict(self.carte_bataille),
            "joueur_humain": self.joueur_humain.to_dict(),
            "joueur_ia": self.joueur_ia.to_dict(),
            "duo_humain": self._duo_ids(self.joueur_humain),
            "duo_ia": self._duo_ids(self.joueur_ia) if duo_ia_visible else None,
            "duo_ia_revele": [inst.template.id for inst in self.reveles_ia],
            "revelation_courante": self.revelation_courante,
            "duos_legaux": [
                sorted(inst.template.id for inst in duo)
                for duo in self._duos_legaux(self.joueur_humain)
            ],
            "ciblages_requis": [
                {
                    "combattant_id": c.template.id,
                    "nom": c.template.nom,
                    "pouvoir": c.template.pouvoir["description"],
                    "cibles": [
                        {"id": adv.template.id, "nom": adv.template.nom}
                        for adv in self.camp_ia.combattants
                    ],
                }
                for c in self.ciblages_requis()
            ] if self.phase == PHASE_CIBLAGE else [],
            "dernier_resultat": self.dernier_resultat,
            "terminee": self.terminee,
            "vainqueur": self.vainqueur,
            "pv_depart": PV_DEPART,
        }
