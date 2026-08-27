"""Orchestration d'une Partie d'Urban Eredan : mise en place, duels, batailles, IA."""
import json
import random

from .batailles import Deck, LIBELLE_CARAC
from .capacites import CONDITIONS_FIN_DE_DUEL
from .ia import choisir_combattant
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

        # La pioche de cartes Bataille, commune aux deux joueurs et persistante pour
        # toute la partie : elle n'est remelangee que lorsqu'elle est epuisee.
        self.deck = Deck()

        self.duel_numero = 1
        self.j1 = random.choice([self.joueur_humain, self.joueur_ia])
        self.j2 = self.joueur_ia if self.j1 is self.joueur_humain else self.joueur_humain
        self.historique = []
        # Issue du duel precedent pour chaque camp ("victoire" / "defaite"), lue par les
        # conditions de capacite `vengeance` et `confiance`.
        self.issue_precedente = {"humain": None, "ia": None}
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
        """Les caracteristiques avec lesquelles ce Combattant dispute les batailles : celles
        de sa carte, une couleur eventuellement ramenee a 0 par une capacite adverse."""
        if self.caracs_duel is not None:
            return self.caracs_duel[role]
        return self._combattant(role).template.caracs

    def _camp(self, role):
        """"humain" ou "ia" pour le joueur qui tient ce role dans le duel en cours."""
        return "humain" if self._joueur(role) is self.joueur_humain else "ia"

    # ------------------------------------------------------------- capacites
    def _capacite(self, role):
        combattant = self._combattant(role)
        return combattant.template.capacite if combattant else None

    def _condition_remplie(self, role, condition, gagnants_roles=None):
        """La condition d'une capacite est-elle remplie pour ce role ? `gagnants_roles`
        n'est connu qu'a la resolution du duel : les conditions `victoire` et `defaite` ne
        sont donc jamais remplies avant."""
        if condition is None:
            return True
        if condition == "premier":
            return role == "j1"
        if condition == "second":
            return role == "j2"
        if condition == "vengeance":
            return self.issue_precedente[self._camp(role)] == "defaite"
        if condition == "confiance":
            return self.issue_precedente[self._camp(role)] == "victoire"
        if gagnants_roles is None:
            return False
        if condition == "victoire":
            return role in gagnants_roles
        return role not in gagnants_roles  # defaite

    def _valeur_multiplicateur(self, multiplicateur, role):
        """Combien de fois l'effet est applique. Un multiplicateur peut valoir 0 (une
        capacite `par bataille remportee` ne produit rien si aucune bataille n'est gagnee)."""
        if multiplicateur is None:
            return 1
        if multiplicateur == "patience":
            return self.duel_numero
        if multiplicateur == "impatience":
            return NB_DUELS_MAX - self.duel_numero + 1
        if multiplicateur == "par_bataille_remportee":
            return len(self.batailles[role])
        return len(self.batailles[ROLE_OPPOSE[role]])  # par_bataille_perdue

    def _preparer_passifs(self):
        """Fige les capacites qui agissent pendant les batailles, une fois les deux
        Combattants engages et avant la premiere carte revelee : `annule_couleur` ramene a 0
        la caracteristique visee chez l'adversaire, `initiative` fait remporter les batailles
        que la condition ne tranche pas."""
        self.caracs_duel = {
            role: dict(self._combattant(role).template.caracs) for role in ("j1", "j2")
        }
        self.initiative = {"j1": False, "j2": False}
        self.annulations = {"j1": None, "j2": None}
        self.capacites_passives = []

        for role in ("j1", "j2"):
            capacite = self._capacite(role)
            if capacite is None or not capacite.passive:
                continue
            if not self._condition_remplie(role, capacite.condition):
                continue
            nom = self._combattant(role).template.nom
            entree = {
                "role": role,
                "camp": self._camp(role),
                "combattant": nom,
                "libelle": capacite.libelle(),
            }
            if capacite.effet.type == "initiative":
                self.initiative[role] = True
                entree["texte"] = f"{nom} (Initiative) remporte les batailles nulles"
            else:
                carac = capacite.effet.carac_annulee
                cible = ROLE_OPPOSE[role]
                self.caracs_duel[cible][carac] = 0
                self.annulations[cible] = carac
                entree["texte"] = (
                    f"{nom} annule la {LIBELLE_CARAC[carac]} de "
                    f"{self._combattant(cible).template.nom} (0 pour ce duel)"
                )
            self.capacites_passives.append(entree)

        self.statuts_capacites = {role: self._capacite_dict(role) for role in ("j1", "j2")}

        if self.initiative["j1"] and self.initiative["j2"]:
            # Les deux Combattants remportent les egalites : elles se neutralisent et la
            # bataille reste nulle.
            self.capacites_passives.append({
                "role": None,
                "camp": None,
                "combattant": None,
                "libelle": "Initiative",
                "texte": "Les deux Combattants ont l'Initiative : les egalites restent nulles",
            })

    def _capacites_resolution(self, gagnants_roles):
        """Applique les capacites qui agissent a la resolution du duel et retourne
        (Degats effectifs par role, variation de PV par camp, journal des capacites).

        Les modificateurs de Degats sont calcules avant que les Degats ne soient retires ;
        les effets de PV (gain, perte, vampirisme) s'appliquent ensuite."""
        degats = {}
        modificateurs = {"j1": 0, "j2": 0}
        effets_pv = {"humain": 0, "ia": 0}
        journal = []

        for role in ("j1", "j2"):
            capacite = self._capacite(role)
            if capacite is None or capacite.passive:
                continue
            if not self._condition_remplie(role, capacite.condition, gagnants_roles):
                continue
            multiplicateur = self._valeur_multiplicateur(capacite.multiplicateur, role)
            valeur = capacite.effet.valeur * multiplicateur
            if valeur <= 0:
                continue

            nom = self._combattant(role).template.nom
            camp = self._camp(role)
            camp_adverse = self._camp(ROLE_OPPOSE[role])
            type_effet = capacite.effet.type
            # Un modificateur de Degats ne change rien si le Combattant concerne ne remporte
            # pas le duel : l'effet est bien applique, mais il n'est pas rapporte au joueur.
            observable = True

            if type_effet == "degats_soi":
                modificateurs[role] += valeur
                observable = role in gagnants_roles
                texte = f"{nom} inflige {valeur} Degats de plus"
            elif type_effet == "degats_adverse":
                modificateurs[ROLE_OPPOSE[role]] -= valeur
                observable = ROLE_OPPOSE[role] in gagnants_roles
                texte = (
                    f"{nom} retire {valeur} Degats a "
                    f"{self._combattant(ROLE_OPPOSE[role]).template.nom}"
                )
            elif type_effet == "pv_soi":
                effets_pv[camp] += valeur
                texte = f"{nom} fait gagner {valeur} PV a son joueur"
            elif type_effet == "pv_adverse":
                effets_pv[camp_adverse] -= valeur
                texte = f"{nom} retire {valeur} PV a l'adversaire"
            else:  # vampirisme
                effets_pv[camp] += valeur
                effets_pv[camp_adverse] -= valeur
                texte = f"{nom} vampirise {valeur} PV"

            if not observable:
                continue

            journal.append({
                "role": role,
                "camp": camp,
                "combattant": nom,
                "libelle": capacite.libelle(),
                "multiplicateur": multiplicateur,
                "valeur": valeur,
                "texte": texte,
            })

        for role in ("j1", "j2"):
            base = self._combattant(role).template.degats
            degats[role] = max(0, base + modificateurs[role])

        return degats, effets_pv, journal

    def _capacite_dict(self, role, gagnants_roles=None):
        """La capacite du Combattant engage, avec son statut dans le duel en cours :
        `active`, `inactive`, ou `en_attente` tant que son issue depend du resultat du duel."""
        capacite = self._capacite(role)
        if capacite is None:
            return None
        if gagnants_roles is None and capacite.condition in CONDITIONS_FIN_DE_DUEL:
            statut = "en_attente"
        else:
            statut = (
                "active"
                if self._condition_remplie(role, capacite.condition, gagnants_roles)
                else "inactive"
            )
        data = capacite.to_dict()
        data["statut"] = statut
        return data

    # ------------------------------------------------------------------ duel
    def _initialiser_duel(self):
        self.combattant_j1 = None
        self.combattant_j2 = None
        # Capacites passives : figees des que les deux Combattants sont engages.
        self.caracs_duel = None
        self.initiative = {"j1": False, "j2": False}
        self.annulations = {"j1": None, "j2": None}
        self.capacites_passives = []
        # Statut des capacites tel qu'il etait a l'engagement des Combattants : figer ce
        # cliche evite d'exposer, pendant que les batailles defilent a l'ecran, un statut
        # recalcule apres la resolution du duel.
        self.statuts_capacites = {"j1": None, "j2": None}
        self.batailles = {"j1": [], "j2": []}
        self.nulles = []
        self.journal_batailles = []
        self.phase = "choix_combattant"
        self.dernier_resultat = None
        self._avancer()

    def _avancer(self):
        """Fait jouer l'IA tant que c'est a elle d'agir, et rend la main des qu'une
        decision revient au joueur humain (ou que le duel est resolu). Une fois en phase
        batailles, il n'y a plus de decision a prendre : la revelation des cartes est
        automatique et attend simplement l'action explicite du joueur."""
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
                self._preparer_passifs()
                self.phase = "batailles"
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

    def reveler_carte(self):
        """Revele automatiquement la prochaine carte Bataille de la pioche commune."""
        if self.phase != "batailles":
            raise ErreurPartie("Ce n'est pas la phase de resolution des batailles")

        self._jouer_bataille()
        self._avancer()
        return self.etat_dict()

    # -------------------------------------------------------------- batailles
    def _jouer_bataille(self):
        """Revele la carte du dessus de la pioche, resout sa condition et l'attribue au
        vainqueur ; si la bataille est nulle, la carte est ecartee."""
        carte = self.deck.piocher()
        gagnant_role = carte.resoudre(self._caracs("j1"), self._caracs("j2"))

        # Initiative : le Combattant remporte les batailles que la condition ne tranche pas.
        # Si les deux l'ont, elles se neutralisent et la bataille reste nulle.
        par_initiative = False
        if gagnant_role is None and self.initiative["j1"] != self.initiative["j2"]:
            gagnant_role = "j1" if self.initiative["j1"] else "j2"
            par_initiative = True

        if gagnant_role is None:
            self.nulles.append(carte)
        else:
            self.batailles[gagnant_role].append(carte)

        self.journal_batailles.append({
            "numero": len(self.journal_batailles) + 1,
            "carte": carte.to_dict(revele=True),
            "valeurs": {
                "j1": carte.detail(self._caracs("j1")),
                "j2": carte.detail(self._caracs("j2")),
            },
            "gagnant_role": gagnant_role,
            "par_initiative": par_initiative,
            "gagnant_camp": self._camp(gagnant_role) if gagnant_role else None,
            "gagnant_nom": self._combattant(gagnant_role).template.nom if gagnant_role else None,
            "score": self._score(),
        })

        if self._duel_termine():
            self._conclure_duel()

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
            if entree["gagnant_nom"]:
                issue = f"{entree['gagnant_nom']} remporte la bataille"
                if entree["par_initiative"]:
                    issue += " (Initiative)"
            else:
                issue = "bataille nulle"
            log.append(
                f"Bataille {entree['numero']} - {carte['nom']} ({carte['condition']}) : "
                f"{valeurs} -> {issue}"
            )

        if par_plafond:
            log.append(
                f"{CARTES_MAX_PAR_DUEL} cartes revelees sans 3 batailles : "
                f"le score ({score['j1']}-{score['j2']}) tranche le duel"
            )

        # Capacites : les passifs ont deja agi pendant les batailles, les effets de
        # resolution s'appliquent maintenant (Degats modifies avant d'etre retires, puis PV).
        degats_effectifs, effets_pv, capacites_resolution = self._capacites_resolution(
            gagnants_roles
        )
        capacites = self.capacites_passives + capacites_resolution
        for entree in capacites:
            log.append("Capacite - " + entree["texte"])

        if len(gagnants_roles) == 2:
            log.append("Double victoire : les deux Combattants infligent leurs Degats")

        pv_debut = {"humain": self.joueur_humain.pv, "ia": self.joueur_ia.pv}
        degats = {}
        for role in gagnants_roles:
            combattant = self._combattant(role)
            adversaire = self._joueur(ROLE_OPPOSE[role])
            valeur = degats_effectifs[role]
            base = combattant.template.degats
            adversaire.pv -= valeur
            degats[combattant.template.nom] = valeur
            log.append(
                f"{combattant.template.nom} remporte le duel {score[role]}-{score[ROLE_OPPOSE[role]]} "
                f"et inflige {valeur} Degats" + ("" if valeur == base else f" ({base} de base)")
            )

        for camp, variation in effets_pv.items():
            if variation:
                joueur = self.joueur_humain if camp == "humain" else self.joueur_ia
                joueur.pv += variation

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
            "capacites": capacites,
            "effets_pv": effets_pv,
            # PV des deux joueurs avant les Degats et les effets de PV de ce duel : le
            # frontend s'en sert pour rejouer le duel sans devoiler son issue.
            "pv_debut": pv_debut,
            "pv_fin": {"humain": self.joueur_humain.pv, "ia": self.joueur_ia.pv},
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
                "degats": degats_effectifs[role],
                "degats_base": combattant.template.degats,
                "capacite": self._capacite_dict(role, gagnants_roles),
            }

        # Memoire pour les conditions `vengeance` / `confiance` du duel suivant : mise a
        # jour apres la construction du resultat, dont les statuts de capacite decrivent le
        # duel qui vient de se jouer.
        for role in ("j1", "j2"):
            self.issue_precedente[self._camp(role)] = (
                "victoire" if role in gagnants_roles else "defaite"
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
            "score": self._score(),
            "caracs_duel": self.caracs_duel,
            "annulations": self.annulations,
            "initiative": self.initiative,
            "capacites_duel": {
                role: (
                    self.statuts_capacites[role]
                    if self.statuts_capacites[role] is not None
                    else (self._capacite_dict(role) if self._combattant(role) else None)
                )
                for role in ("j1", "j2")
            },
            "capacites_passives": self.capacites_passives,
            "cartes_revelees": self._cartes_revelees(),
            "journal_batailles": self.journal_batailles,
            "deck_restantes": self.deck.cartes_restantes(),
            "compteur_couleurs": dict(self.deck.compteurs),
            "dernier_resultat": self.dernier_resultat,
            "terminee": self.terminee,
            "vainqueur": self.vainqueur,
        }
