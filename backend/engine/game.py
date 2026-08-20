"""Orchestration d'une partie d'Urban Eredan (version Eredice) : mise en place, piste
d'initiative, rounds de draft de Des, fin de match."""
import random
from collections import Counter

from .capacites import capacites_activables, resoudre_activations
from .ia import choisir_action
from .models import (
    COULEURS,
    NB_DES_POOL,
    PV_DEPART,
    De,
    Joueur,
    PersonnageEnJeu,
    lancer_pool,
)

TAILLE_EQUIPE = 3
# Le match ne s'acheve normalement que par KO ; ce plafond est un garde-fou contre les
# parties infinies (deux equipes trop defensives). Au-dela, le joueur avec le plus de PV
# l'emporte.
ROUNDS_MAX = 15


class ErreurPartie(Exception):
    pass


class Partie:
    def __init__(self, templates_par_id, equipe_joueur_ids):
        if len(equipe_joueur_ids) != TAILLE_EQUIPE or len(set(equipe_joueur_ids)) != TAILLE_EQUIPE:
            raise ErreurPartie(f"L'equipe doit comporter {TAILLE_EQUIPE} Personnages distincts")
        for pid in equipe_joueur_ids:
            if pid not in templates_par_id:
                raise ErreurPartie(f"Personnage inconnu : {pid}")

        restants = [pid for pid in templates_par_id if pid not in equipe_joueur_ids]
        if len(restants) < TAILLE_EQUIPE:
            raise ErreurPartie("Pas assez de Personnages pour constituer l'equipe adverse")
        equipe_ia_ids = random.sample(restants, TAILLE_EQUIPE)

        self.joueur_humain = Joueur("humain", False)
        self.joueur_ia = Joueur("ia", True)
        self.joueur_humain.equipe = [
            PersonnageEnJeu(templates_par_id[pid], self.joueur_humain) for pid in equipe_joueur_ids
        ]
        self.joueur_ia.equipe = [
            PersonnageEnJeu(templates_par_id[pid], self.joueur_ia) for pid in equipe_ia_ids
        ]

        # Piste d'initiative : les 6 Personnages des deux equipes, melanges au centre par
        # ordre croissant d'Initiative (la plus basse drafte en premier). Les valeurs
        # d'Initiative ne servent qu'a ce placement initial ; ensuite, seules les places
        # comptent (cf. effet `initiative`). Egalites tranchees au hasard.
        tous = self.joueur_humain.equipe + self.joueur_ia.equipe
        random.shuffle(tous)
        self.piste = sorted(tous, key=lambda p: p.template.initiative)

        self.round_numero = 0
        self.pool = []
        self.sequence = []
        self.index_sequence = 0
        self.journal = []
        self.terminee = False
        self.vainqueur = None

        self.log("Les equipes sont revelees.")
        self.log(
            "Piste d'initiative : "
            + " -> ".join(f"{p.template.nom} ({p.joueur.nom})" for p in self.piste)
        )
        self._demarrer_round()
        self._boucle()

    # ------------------------------------------------------------------ journal
    def log(self, message):
        self.journal.append(message)

    # -------------------------------------------------------- acces pour capacites
    def adversaire(self, joueur):
        return self.joueur_ia if joueur is self.joueur_humain else self.joueur_humain

    def position_piste(self, perso):
        return self.piste.index(perso)

    def deplacer_piste(self, perso, places):
        """Deplace le Personnage de `places` positions vers l'avant de la piste
        (valeur negative : vers l'arriere), par echanges successifs avec son voisin.
        Retourne la nouvelle position."""
        i = self.piste.index(perso)
        cible = max(0, min(len(self.piste) - 1, i - places))
        pas = 1 if cible > i else -1
        while i != cible:
            self.piste[i], self.piste[i + pas] = self.piste[i + pas], self.piste[i]
            i += pas
        return cible

    def modifier_pv(self, joueur, delta, source):
        if delta == 0:
            return
        avant = joueur.pv
        joueur.pv = max(0, joueur.pv + delta)
        signe = "+" if delta > 0 else ""
        self.log(f"{source} : {joueur.nom} {signe}{delta} PV ({avant} -> {joueur.pv})")
        self._verifier_fin()

    def retirer_du_pool_meilleure_couleur(self):
        """Retire du pool un De de la couleur la plus abondante (egalite : ordre
        rouge > bleu > jaune). Retourne None si le pool est vide."""
        if not self.pool:
            return None
        compte = Counter(d.couleur for d in self.pool)
        couleur = min(COULEURS, key=lambda c: (-compte[c], COULEURS.index(c)))
        de = next(d for d in self.pool if d.couleur == couleur)
        self.pool.remove(de)
        return de

    def relancer_pool(self):
        for de in self.pool:
            de.relancer()
        return len(self.pool)

    # --------------------------------------------------------------- rounds
    def _demarrer_round(self):
        self.round_numero += 1
        self.pool = lancer_pool(NB_DES_POOL)
        # La sequence de draft du round est figee au debut du round : un creneau par
        # Personnage de la piste. Un deplacement d'Initiative en cours de round modifie
        # donc la piste, mais ne prend effet qu'au round suivant.
        self.sequence = list(self.piste)
        self.index_sequence = 0
        for perso in self.piste:
            perso.a_attaque = False
        self.log(
            f"--- Round {self.round_numero} --- Des tires : "
            + ", ".join(d.couleur for d in self.pool)
        )

    def _terminer_round(self):
        if self.pool:
            self.log(
                "Fin du round, De(s) non drafte(s) defausse(s) : "
                + ", ".join(d.couleur for d in self.pool)
            )
        if self.round_numero >= ROUNDS_MAX:
            self._fin_par_pv()
            return
        self._demarrer_round()

    def _fin_par_pv(self):
        self.terminee = True
        pv_h, pv_i = self.joueur_humain.pv, self.joueur_ia.pv
        if pv_h > pv_i:
            self.vainqueur = "humain"
        elif pv_i > pv_h:
            self.vainqueur = "ia"
        else:
            self.vainqueur = None
        self.log(
            f"Limite de {ROUNDS_MAX} rounds atteinte : victoire aux PV "
            f"(humain {pv_h} / ia {pv_i})"
        )

    def _verifier_fin(self):
        pv_h, pv_i = self.joueur_humain.pv, self.joueur_ia.pv
        if pv_h > 0 and pv_i > 0:
            return
        self.terminee = True
        if pv_h <= 0 and pv_i <= 0:
            self.vainqueur = None
        elif pv_h <= 0:
            self.vainqueur = "ia"
        else:
            self.vainqueur = "humain"
        self.log("KO : la partie est terminee.")

    # ---------------------------------------------------------------- boucle
    def creneau_courant(self):
        if self.terminee or self.index_sequence >= len(self.sequence):
            return None
        return self.sequence[self.index_sequence]

    def joueur_courant(self):
        creneau = self.creneau_courant()
        return creneau.joueur if creneau else None

    def _boucle(self):
        """Avance la partie jusqu'a ce que ce soit au joueur humain d'agir (ou que la
        partie soit terminee) : saute les creneaux impossibles (pool vide), enchaine les
        rounds et joue automatiquement les creneaux de l'IA."""
        garde = 0
        while not self.terminee:
            garde += 1
            if garde > 1000:
                self.log("Garde-fou : boucle de jeu interrompue.")
                self.terminee = True
                return
            if self.index_sequence >= len(self.sequence):
                self._terminer_round()
                continue
            creneau = self.sequence[self.index_sequence]
            if not self.pool:
                self.log(
                    f"Pool epuise : le creneau de {creneau.template.nom} est perdu."
                )
                self.index_sequence += 1
                continue
            if not creneau.joueur.est_ia:
                return
            self._jouer_ia(creneau)

    def _jouer_ia(self, creneau):
        de, perso, usage = choisir_action(self, creneau.joueur)
        self._appliquer_draft(creneau.joueur, de, perso, usage)
        self.index_sequence += 1

    # ---------------------------------------------------------------- actions
    def drafter(self, de_id, personnage_id, usage):
        """Action du joueur humain : drafter un De du pool et l'affecter a l'un de ses
        Personnages, soit en ressource (`stock`), soit pour declencher son attaque de
        base (`attaque`)."""
        if self.terminee:
            raise ErreurPartie("La partie est terminee")
        creneau = self.creneau_courant()
        if creneau is None or creneau.joueur.est_ia:
            raise ErreurPartie("Ce n'est pas ton creneau de draft")
        joueur = creneau.joueur

        de = next((d for d in self.pool if d.id == de_id), None)
        if de is None:
            raise ErreurPartie("Ce De n'est pas disponible dans le pool")
        perso = joueur.personnage(personnage_id)
        if perso is None:
            raise ErreurPartie("Ce Personnage n'appartient pas a ton equipe")
        if usage not in ("stock", "attaque"):
            raise ErreurPartie("Usage invalide (attendu : 'stock' ou 'attaque')")
        if usage == "attaque" and perso.a_attaque:
            raise ErreurPartie(f"{perso.template.nom} a deja attaque ce round")

        self._appliquer_draft(joueur, de, perso, usage)
        self.index_sequence += 1
        self._boucle()
        return self.etat_dict()

    def _appliquer_draft(self, joueur, de, perso, usage):
        self.pool.remove(de)
        if usage == "attaque":
            perso.a_attaque = True
            self.log(
                f"{joueur.nom} depense un De {de.couleur} : attaque de base de "
                f"{perso.template.nom}"
            )
            self.modifier_pv(self.adversaire(joueur), -perso.attaque, f"Attaque de {perso.template.nom}")
        else:
            perso.des_stockes.append(de)
            self.log(
                f"{joueur.nom} assigne un De {de.couleur} a {perso.template.nom} "
                f"({len(perso.des_stockes)} De(s) stocke(s))"
            )
            resoudre_activations(self, perso)

    # ------------------------------------------------------------------- etat
    def _declencheurs(self, perso):
        """Couleurs qui, ajoutees a ce Personnage, declencheraient au moins une
        Capacite (indice visuel pour le joueur)."""
        declencheurs = []
        for couleur in COULEURS:
            temoin = De(couleur)
            perso.des_stockes.append(temoin)
            if capacites_activables(perso, self):
                declencheurs.append(couleur)
            perso.des_stockes.remove(temoin)
        return declencheurs

    def _personnage_dict(self, perso):
        data = perso.to_dict(position_piste=self.position_piste(perso))
        data["declencheurs"] = self._declencheurs(perso)
        return data

    def _joueur_dict(self, joueur):
        return {
            "nom": joueur.nom,
            "est_ia": joueur.est_ia,
            "pv": joueur.pv,
            "pv_depart": PV_DEPART,
            "equipe": [self._personnage_dict(p) for p in joueur.equipe],
        }

    def etat_dict(self):
        creneau = self.creneau_courant()
        return {
            "round": self.round_numero,
            "rounds_max": ROUNDS_MAX,
            "pool": [d.to_dict() for d in self.pool],
            "piste": [
                {
                    "personnage_id": p.template.id,
                    "nom": p.template.nom,
                    "proprietaire": p.joueur.nom,
                    "position": i,
                }
                for i, p in enumerate(self.piste)
            ],
            "sequence": [
                {
                    "personnage_id": p.template.id,
                    "nom": p.template.nom,
                    "proprietaire": p.joueur.nom,
                    "joue": i < self.index_sequence,
                    "courant": i == self.index_sequence and not self.terminee,
                }
                for i, p in enumerate(self.sequence)
            ],
            "creneau_courant": creneau.template.id if creneau else None,
            "joueur_courant": creneau.joueur.nom if creneau else None,
            "joueur_humain": self._joueur_dict(self.joueur_humain),
            "joueur_ia": self._joueur_dict(self.joueur_ia),
            "journal": self.journal,
            "terminee": self.terminee,
            "vainqueur": self.vainqueur,
        }
