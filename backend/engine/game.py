"""Orchestration d'une partie d'Urban Eredan (version Eredice) : mise en place, piste
d'initiative, rounds de draft de Des, fin de match."""
import random
from collections import Counter

from .capacites import capacites_activables, couleur_utile, resoudre_activations
from .ia import arbitrer_capacite, choisir_action
from .models import (
    COULEURS,
    FACE_EPEE,
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
        # Journal structure : un preambule, puis un bloc par round contenant des
        # entrees ordonnees (actions de draft et evenements). Les consequences d'une
        # action (activation de Capacite, PV, manipulation de Des) sont imbriquees dans
        # cette action, pour que l'interface puisse montrer qui a joue quoi sans avoir a
        # relire toute la liste.
        self.preambule = []
        self.journal = []
        self._action_courante = None
        # Choix de Capacite en attente d'une reponse du joueur humain. Tant qu'il n'est
        # pas tranche, la cascade d'activations et le creneau de draft sont suspendus
        # (cf. `_arbitre_activation` et `choisir_capacite`).
        self.choix_capacite = None
        self.terminee = False
        self.vainqueur = None

        self.log("Les equipes sont revelees.")
        self.log(
            "Piste d'initiative : "
            + " -> ".join(f"{p.template.nom} ({p.joueur.nom})" for p in self.piste)
        )
        self._demarrer_round()
        self._avancer()

    # ------------------------------------------------------------------ journal
    def _conteneur_journal(self):
        """Ou ecrire : dans les consequences de l'action en cours de resolution, sinon
        dans les entrees du round courant, sinon dans le preambule."""
        if self._action_courante is not None:
            return self._action_courante["consequences"]
        if self.journal:
            return self.journal[-1]["entrees"]
        return self.preambule

    def log(self, message, type="info", **champs):
        """Ajoute une entree au journal. `type` sert au rendu (icone, couleur) et
        `champs` transporte les donnees structurees utiles a l'affichage (delta de PV,
        Personnage concerne...) en plus du texte lisible tel quel."""
        entree = {"type": type, "texte": message, **champs}
        if self._action_courante is None:
            entree["genre"] = "evenement"
        self._conteneur_journal().append(entree)

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
        self.log(
            f"{source} : {joueur.nom} {signe}{delta} PV ({avant} -> {joueur.pv})",
            "pv", joueur=joueur.nom, delta=delta, avant=avant, apres=joueur.pv, source=source,
        )
        self._verifier_fin()

    def retirer_du_pool_meilleure_couleur(self):
        """Retire du pool un De de la couleur la plus abondante (egalite : ordre
        rouge > bleu > jaune). Retourne None si le pool est vide ou ne contient plus que
        des epees (jamais stockables)."""
        if not self.pool:
            return None
        compte = Counter(d.couleur for d in self.pool)
        disponibles = [c for c in COULEURS if compte[c] > 0]
        if not disponibles:
            return None
        couleur = min(disponibles, key=lambda c: (-compte[c], COULEURS.index(c)))
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
        self.journal.append({
            "numero": self.round_numero,
            "des_tires": [d.couleur for d in self.pool],
            "entrees": [],
        })

    def _terminer_round(self):
        if self.pool:
            self.log(
                "Des non draftes, defausses en fin de round : "
                + ", ".join(d.couleur for d in self.pool),
                "fin_round", des=[d.couleur for d in self.pool],
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
            f"(humain {pv_h} / ia {pv_i})",
            "fin_match",
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
        self.log("KO : la partie est terminee.", "fin_match")

    # ---------------------------------------------------------------- boucle
    def creneau_courant(self):
        if self.terminee or self.index_sequence >= len(self.sequence):
            return None
        return self.sequence[self.index_sequence]

    def joueur_courant(self):
        creneau = self.creneau_courant()
        return creneau.joueur if creneau else None

    def _avancer(self):
        """Avance jusqu'au prochain creneau jouable : enchaine les rounds et saute les
        creneaux impossibles (pool epuise). S'arrete des que le creneau courant est
        jouable, quel que soit son proprietaire, ou que la partie est terminee.

        L'IA n'est volontairement PAS jouee ici : ses creneaux sont resolus un par un via
        `jouer_creneau_ia()`, pour que l'interface puisse animer chacun de ses choix."""
        garde = 0
        while not self.terminee:
            garde += 1
            if garde > 1000:
                self.log("Garde-fou : boucle de jeu interrompue.", "fin_match")
                self.terminee = True
                return
            if self.index_sequence >= len(self.sequence):
                self._terminer_round()
                continue
            creneau = self.sequence[self.index_sequence]
            if not self.pool:
                self.log(
                    f"Pool epuise : le creneau de {creneau.template.nom} est perdu.",
                    "creneau_perdu",
                )
                self.index_sequence += 1
                continue
            return

    # ----------------------------------------------------- choix de Capacite
    def _arbitre_activation(self, perso, options):
        """Arbitre appele par la cascade quand plusieurs Capacites d'un meme Personnage
        sont payables en meme temps. L'IA tranche seule ; pour le joueur humain, on
        enregistre le choix a faire et on suspend la cascade (retour None)."""
        if perso.joueur.est_ia:
            return arbitrer_capacite(perso, options, self)
        self.choix_capacite = {
            "personnage": perso,
            "action": self._action_courante,
            "options": options,
        }
        self.log(
            f"{perso.template.nom} : {len(options)} Capacites payables, a toi de choisir",
            "choix", personnage=perso.template.nom, personnage_id=perso.template.id,
        )
        return None

    def choisir_capacite(self, indice):
        """Tranche le choix en attente et reprend la cascade la ou elle a ete suspendue.

        Les activations qui suivent restent imbriquees dans l'action de draft d'origine :
        c'est bien ce De qui les a declenchees."""
        if self.terminee:
            raise ErreurPartie("La partie est terminee")
        choix = self.choix_capacite
        if choix is None:
            raise ErreurPartie("Aucun choix de Capacite en attente")
        if indice not in [i for i, _, _ in choix["options"]]:
            raise ErreurPartie("Cette Capacite n'est pas activable maintenant")
        self.choix_capacite = None
        self._action_courante = choix["action"]
        try:
            resoudre_activations(
                self, choix["personnage"], self._arbitre_activation, indice
            )
        finally:
            self._action_courante = None
        self._terminer_creneau()
        return self.etat_dict()

    # ---------------------------------------------------------------- actions
    def _terminer_creneau(self):
        """Passe au creneau suivant -- sauf si un choix de Capacite est en attente : le
        creneau reste alors ouvert jusqu'a ce qu'il soit tranche."""
        if self.choix_capacite is not None:
            return
        self.index_sequence += 1
        self._avancer()

    def jouer_creneau_ia(self):
        """Resout le creneau courant de l'IA, et un seul."""
        if self.terminee:
            raise ErreurPartie("La partie est terminee")
        if self.choix_capacite is not None:
            raise ErreurPartie("Une Capacite doit d'abord etre choisie")
        creneau = self.creneau_courant()
        if creneau is None or not creneau.joueur.est_ia:
            raise ErreurPartie("Ce n'est pas le creneau de l'IA")
        de, perso, usage = choisir_action(self, creneau.joueur)
        self._appliquer_draft(creneau.joueur, de, perso, usage, creneau)
        self._terminer_creneau()
        return self.etat_dict()

    def drafter(self, de_id, personnage_id, usage):
        """Action du joueur humain : drafter un De du pool et l'affecter a l'un de ses
        Personnages, selon l'usage choisi :
        - `stock` : le De (couleur) devient une ressource stockee sur ce Personnage --
          sauf si aucune de ses Capacites n'a de case de cette couleur (ni de joker),
          auquel cas le De est perdu.
        - `attaque` : le De (epee) declenche l'attaque de base de ce Personnage."""
        if self.terminee:
            raise ErreurPartie("La partie est terminee")
        if self.choix_capacite is not None:
            raise ErreurPartie("Une Capacite doit d'abord etre choisie")
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
        if usage == "stock" and de.couleur == FACE_EPEE:
            raise ErreurPartie("Une epee ne peut pas etre stockee")
        if usage == "attaque" and de.couleur != FACE_EPEE:
            raise ErreurPartie("Seule une epee peut declencher une attaque")

        self._appliquer_draft(joueur, de, perso, usage, creneau)
        self._terminer_creneau()
        return self.etat_dict()

    def _appliquer_draft(self, joueur, de, perso, usage, creneau):
        """Applique un draft et l'enregistre comme une action du journal : tout ce que ce
        De declenche (Capacites, PV, manipulation de Des) est imbrique dans cette action
        via `_action_courante`."""
        action = {
            "genre": "action",
            "joueur": joueur.nom,
            "creneau": creneau.template.nom,
            "de": de.couleur,
            "personnage": perso.template.nom,
            "personnage_id": perso.template.id,
            "usage": usage,
            "consequences": [],
        }
        self.journal[-1]["entrees"].append(action)
        self._action_courante = action
        try:
            self.pool.remove(de)
            if usage == "attaque":
                action["degats"] = perso.attaque
                self.modifier_pv(
                    self.adversaire(joueur), -perso.attaque,
                    f"Attaque de {perso.template.nom}",
                )
            elif couleur_utile(perso, de.couleur):
                perso.des_stockes.append(de)
                action["des_stockes"] = len(perso.des_stockes)
                resoudre_activations(self, perso, self._arbitre_activation)
            else:
                action["perdu"] = True
                self.log(
                    f"{perso.template.nom} : De {de.couleur} perdu "
                    "(aucune de ses Capacites ne l'utilise)",
                    "de_perdu", personnage=perso.template.nom, couleur=de.couleur,
                )
        finally:
            self._action_courante = None

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

    def _choix_dict(self):
        """Le choix de Capacite attendu du joueur humain, ou None. Les options portent le
        paiement exact qui serait defausse, pour que le joueur decide en connaissance."""
        choix = self.choix_capacite
        if choix is None:
            return None
        return {
            "personnage_id": choix["personnage"].template.id,
            "nom": choix["personnage"].template.nom,
            "options": [
                {
                    "indice": indice,
                    "description": capacite.get("description", ""),
                    "cout": capacite.get("cout", []),
                    "paiement": [d.couleur for d in paiement],
                }
                for indice, capacite, paiement in choix["options"]
            ],
        }

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
            "choix_capacite": self._choix_dict(),
            "joueur_humain": self._joueur_dict(self.joueur_humain),
            "joueur_ia": self._joueur_dict(self.joueur_ia),
            "preambule": self.preambule,
            "journal": self.journal,
            "terminee": self.terminee,
            "vainqueur": self.vainqueur,
        }
