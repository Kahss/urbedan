"""Moteur de resolution des Pouvoirs, version duo : 2 Combattants par camp.

Hypotheses de resolution retenues (voir README.md, section version duo) :
- Les Glyphes ont disparu : l'Energie n'existe plus, et le Pouvoir unique de chaque
  Combattant est donc TOUJOURS actif (plus de seuil `energie_min`, plus de modificateurs
  `par_energie*`).
- Une bataille oppose deux camps de 2 Combattants. La Puissance d'un camp est la somme
  des Puissances de ses 2 Combattants ; le camp de plus forte somme remporte la bataille.
  En cas d'egalite, les deux camps la remportent (double victoire).
- Le camp vainqueur inflige a l'adversaire la somme des Degats de ses 2 Combattants.
- Les camps conservent un ordre J1 / J2 (le vainqueur de la bataille precedente est J1).
  Le camp J1 resout les Pouvoirs de ses 2 Combattants (dans l'ordre du duo) avant le camp
  J2. Les conditions `courage` / `riposte` se lisent desormais "mon camp resout en
  premier / en second".
- Un malus de `degats` dirige vers l'adversaire porte sur le TOTAL des Degats du duo
  adverse, et non sur un Combattant en particulier : il ne demande donc aucun ciblage
  (c'est le duo entier qui frappe, c'est le duo entier qu'on affaiblit). Le total d'un
  camp ne descend jamais sous 0.
- Un effet a cible unique (Puissance adverse, Stop pouvoir, Copie pouvoir, Echange) vise
  UN des 2 Combattants adverses, designe par le joueur apres revelation des deux duos
  (`CombattantBataille.cible`). Un Pouvoir ne designe qu'une seule cible, meme s'il porte
  plusieurs effets a cible unique.
- Les effets `vie` et `vampirisme` portent sur les PV d'un joueur, pas sur un Combattant :
  ils ne demandent donc aucun ciblage.
- `protection` protege le CAMP entier de son porteur : elle annule les modifications
  adverses deja subies par ses 2 Combattants (et par les PV du joueur) et bloque toute
  nouvelle modification adverse pour le reste de la bataille. Sans cela, l'adversaire se
  contenterait de designer l'autre Combattant du duo.
- Une bataille se resout en 2 passes : Pass 1 (Pouvoirs immediats), determination du camp
  vainqueur, puis Pass 2 (Pouvoirs conditionnes par Victoire / Defaite / Surpuissance, ou
  portant le modificateur Contrecoup).
- `surpuissance` se compare sur les sommes de Puissance figees au moment de la
  determination du vainqueur, pour qu'un Pouvoir de la passe differee ne puisse pas
  reecrire a posteriori le critere qui l'a declenche.
- `contrecoup` retourne sur son porteur l'effet normalement dirige vers l'adversaire, et
  uniquement si son camp remporte la bataille (conforme a pouvoirs.csv ; l'implementation
  de la version de base omettait cette redirection et soignait donc l'adversaire).
- Nouvelles conditions de la version duo : `premiere_fois` / `seconde_fois`, satisfaites
  selon que le Combattant est engage pour la premiere ou la seconde fois de la partie.
- Conditions a seuil, comparees aux caracteristiques de BASE (celles imprimees sur la
  carte, avant tout Pouvoir) pour rester independantes de l'ordre de resolution :
  `puissance_alliee` (le coequipier du duo), `puissance_base_adverse` / `degats_base_adverse`
  (au moins un des 2 Combattants adverses). Le seuil est porte par le champ `seuil` du
  Pouvoir.
- La carte bataille `Depasser ses limites` pose `CampBataille.conditions_forcees` : toutes
  les conditions des Pouvoirs de ce camp sont alors tenues pour validees, y compris
  `victoire` ET `defaite` simultanement.
"""

TYPES_CIBLE_UNIQUE = ("stop_pouvoir", "copie_pouvoir", "echange")
CONDITIONS_DIFFEREES = ("victoire", "defaite", "surpuissance")


def pouvoir_requiert_cible(pouvoir):
    """Le Pouvoir porte-t-il au moins un effet a cible unique, obligeant son proprietaire
    a designer l'un des 2 Combattants adverses ?"""
    if pouvoir is None:
        return False
    contrecoup = pouvoir.get("modificateur") == "contrecoup"
    for effet in pouvoir.get("effets", []):
        type_effet = effet["type"]
        if type_effet in TYPES_CIBLE_UNIQUE:
            return True
        # Un malus de `degats` adverse porte sur le total du duo : pas de cible a designer.
        if (
            not contrecoup
            and type_effet == "puissance"
            and effet.get("cible", "soi") == "adversaire"
        ):
            return True
    return False


def _formater_detail(total, detail):
    morceaux = []
    for i, (label, valeur) in enumerate(detail):
        if i == 0:
            morceaux.append(f"{valeur} ({label})")
        else:
            signe = "+" if valeur >= 0 else "-"
            morceaux.append(f"{signe} {abs(valeur)} ({label})")
    return f"{total} = " + " ".join(morceaux)


class CombattantBataille:
    """Un Combattant engage dans la bataille en cours, cote `camp`."""

    def __init__(self, camp, instance, n_utilisation):
        self.camp = camp
        self.instance = instance
        self.template = instance.template
        self.n_utilisation = n_utilisation  # 1 = premiere fois, 2 = seconde fois
        self.puissance = self.template.puissance
        self.degats = self.template.degats
        self.detail_puissance = [("base", self.template.puissance)]
        self.detail_degats = [("base", self.template.degats)]
        self.stoppe = False
        self.cible = None  # CombattantBataille adverse designe par le joueur

    @property
    def joueur(self):
        return self.camp.joueur

    def pouvoir(self):
        """Le Pouvoir du Combattant. Toujours actif dans la version duo : plus d'Energie,
        donc plus de seuil d'activation."""
        return self.template.pouvoir

    def to_dict(self):
        return {
            "id": self.template.id,
            "nom": self.template.nom,
            "n_utilisation": self.n_utilisation,
            "puissance": self.puissance,
            "degats": max(0, self.degats),
            "detail_puissance": self.detail_puissance,
            "detail_degats": self.detail_degats,
            "puissance_txt": _formater_detail(self.puissance, self.detail_puissance),
            "degats_txt": _formater_detail(self.degats, self.detail_degats),
            "pouvoir": self.template.pouvoir,
            "stoppe": self.stoppe,
            "cible": self.cible.template.id if self.cible else None,
            "cible_nom": self.cible.template.nom if self.cible else None,
        }


class CampBataille:
    """Le duo d'un joueur pour la bataille en cours."""

    def __init__(self, joueur, engagements, role):
        """`engagements` : liste de (CombattantEnEquipe, n_utilisation)."""
        self.joueur = joueur
        self.role = role  # "J1" ou "J2"
        self.combattants = [CombattantBataille(self, inst, n) for inst, n in engagements]
        self.protege = False
        self.gagnant = False
        self.adversaire = None
        self.bonus_degats = 0  # carte bataille du tour, et malus de Degats adverses
        self.detail_degats_camp = []
        self.conditions_forcees = False  # carte bataille "Depasser ses limites"
        self.puissance_figee = None  # somme au moment de la determination du vainqueur

    @property
    def camp(self):
        """Permet de traiter uniformement un Combattant et un camp comme cible d'un
        effet : les deux exposent `.camp`."""
        return self

    def puissance_totale(self):
        return sum(c.puissance for c in self.combattants)

    def degats_bruts(self):
        """Somme des Degats du duo, avant application du plancher a 0. Un malus adverse
        (Mage, Ranger, Ensorceleur) se retranche ici, sur le total du duo."""
        return sum(max(0, c.degats) for c in self.combattants) + self.bonus_degats

    def degats_totaux(self):
        return max(0, self.degats_bruts())

    def to_dict(self):
        return {
            "joueur": self.joueur.nom,
            "role": self.role,
            "combattants": [c.to_dict() for c in self.combattants],
            "puissance_totale": self.puissance_totale(),
            "degats_totaux": self.degats_totaux(),
            "bonus_degats": self.bonus_degats,
            "detail_degats_camp": self.detail_degats_camp,
            "gagnant": self.gagnant,
        }


def _valeur_effective(valeur, pouvoir, source):
    modificateur = pouvoir.get("modificateur")
    if modificateur == "patience":
        return valeur * source.camp.tour
    if modificateur == "impatience":
        return valeur * (source.camp.tours_max - source.camp.tour + 1)
    return valeur


def _verifier_condition(pouvoir, source):
    """La condition du Pouvoir est-elle satisfaite pour `source` ?

    Les conditions a seuil se lisent sur les caracteristiques de BASE des Combattants
    concernes : la carte imprimee, jamais la valeur deja modifiee par un Pouvoir. Sans
    quoi le resultat dependrait de l'ordre de resolution des deux camps."""
    camp = source.camp
    if camp.conditions_forcees:
        return True
    condition = pouvoir.get("condition")
    if condition is None:
        return True
    adverse = camp.adversaire
    seuil = pouvoir.get("seuil", 0)
    if condition == "puissance_alliee":
        return any(
            c.template.puissance >= seuil for c in camp.combattants if c is not source
        )
    if condition == "puissance_base_adverse":
        return any(c.template.puissance >= seuil for c in adverse.combattants)
    if condition == "degats_base_adverse":
        return any(c.template.degats >= seuil for c in adverse.combattants)
    if condition == "courage":
        return camp.role == "J1"
    if condition == "riposte":
        return camp.role == "J2"
    if condition == "vengeance":
        return adverse.joueur.pv > camp.joueur.pv
    if condition == "domination":
        return adverse.joueur.pv < camp.joueur.pv
    if condition == "premiere_fois":
        return source.n_utilisation == 1
    if condition == "seconde_fois":
        return source.n_utilisation == 2
    if condition == "victoire":
        return camp.gagnant
    if condition == "defaite":
        return not camp.gagnant
    if condition == "surpuissance":
        return camp.gagnant and camp.puissance_figee >= 2 * adverse.puissance_figee
    return True


def _est_differee(pouvoir):
    return (
        pouvoir.get("condition") in CONDITIONS_DIFFEREES
        or pouvoir.get("modificateur") == "contrecoup"
    )


def _contient_copie_pouvoir(pouvoir):
    return any(effet["type"] == "copie_pouvoir" for effet in pouvoir.get("effets", []))


class MoteurBataille:
    def __init__(self, camp_j1, camp_j2, tour, tours_max, bonus_degats_vainqueur=0):
        self.camp_j1 = camp_j1
        self.camp_j2 = camp_j2
        camp_j1.adversaire = camp_j2
        camp_j2.adversaire = camp_j1
        for camp in (camp_j1, camp_j2):
            camp.tour = tour
            camp.tours_max = tours_max
        self.tour = tour
        self.tours_max = tours_max
        self.bonus_degats_vainqueur = bonus_degats_vainqueur
        self.ledger = []  # {source, cible, champ, valeur, detail_liste, detail_entree}
        self.log = []

    # ------------------------------------------------------------ application
    def _appliquer(self, source, cible, champ, valeur, label):
        """Applique `valeur` au champ `champ` de `cible` (un Combattant pour
        puissance/degats, un camp pour pv), en tracant l'operation dans le ledger pour
        qu'elle reste annulable par un Stop pouvoir retroactif ou une Protection."""
        if valeur == 0:
            return True
        if cible.camp is not source.camp and cible.camp.protege:
            self.log.append(
                f"{source.template.nom} (Pouvoir) est bloque par la Protection du camp "
                f"{cible.camp.joueur.nom}"
            )
            return False
        detail_liste = None
        if champ == "puissance":
            cible.puissance += valeur
            detail_liste = cible.detail_puissance
        elif champ == "degats":
            cible.degats += valeur
            detail_liste = cible.detail_degats
        elif champ == "degats_camp":
            cible.bonus_degats += valeur
            detail_liste = cible.detail_degats_camp
        elif champ == "pv":
            cible.camp.joueur.pv += valeur
        detail_entree = None
        if detail_liste is not None:
            detail_entree = (label, valeur)
            detail_liste.append(detail_entree)
        self.ledger.append({
            "source": source, "cible": cible, "champ": champ, "valeur": valeur,
            "detail_liste": detail_liste, "detail_entree": detail_entree,
        })
        return True

    def _revert(self, record):
        cible, champ, valeur = record["cible"], record["champ"], record["valeur"]
        if champ == "puissance":
            cible.puissance -= valeur
        elif champ == "degats":
            cible.degats -= valeur
        elif champ == "degats_camp":
            cible.bonus_degats -= valeur
        elif champ == "pv":
            cible.camp.joueur.pv -= valeur
        if record["detail_liste"] is not None and record["detail_entree"] in record["detail_liste"]:
            record["detail_liste"].remove(record["detail_entree"])

    def _annuler_pouvoir(self, combattant):
        """Annule le Pouvoir de `combattant` : revert de tous les effets deja produits par
        ce Pouvoir, qu'ils aient porte sur son camp ou sur le camp adverse."""
        combattant.stoppe = True
        restants = []
        annule = False
        for record in self.ledger:
            if record["source"] is combattant:
                self._revert(record)
                annule = True
            else:
                restants.append(record)
        self.ledger = restants
        return annule

    def _nettoyer_effets_adverses(self, camp):
        """Annule toutes les modifications que le camp adverse a deja fait subir a `camp`
        (ses 2 Combattants et les PV de son joueur)."""
        restants = []
        annules = 0
        for record in self.ledger:
            if record["cible"].camp is camp and record["source"].camp is not camp:
                self._revert(record)
                annules += 1
            else:
                restants.append(record)
        self.ledger = restants
        return annules

    # ---------------------------------------------------------------- effets
    def _resoudre_effet(self, source, pouvoir, effet, label=None):
        camp = source.camp
        camp_adverse = camp.adversaire
        type_effet = effet["type"]
        modificateur = pouvoir.get("modificateur")
        label = label or f"Pouvoir {source.template.nom}"

        if type_effet in ("puissance", "degats", "vie"):
            vers_soi = effet.get("cible", "soi") == "soi"
            if modificateur == "contrecoup":
                if not camp.gagnant:
                    self.log.append(
                        f"{source.template.nom} Pouvoir ({pouvoir['description']}) : "
                        "Contrecoup non declenche (pas de victoire)"
                    )
                    return
                # Contrecoup retourne sur son porteur l'effet normalement dirige vers
                # l'adversaire : aucune cible adverse n'est donc a designer.
                vers_soi = True
            valeur = _valeur_effective(effet.get("valeur", 0), pouvoir, source)
            if type_effet == "vie":
                # Les PV appartiennent au joueur, pas a un Combattant : aucun ciblage.
                cible = camp if vers_soi else camp_adverse
                champ = "pv"
                avant = cible.joueur.pv
                nom_cible = cible.joueur.nom
            elif vers_soi:
                cible = source
                champ = type_effet
                avant = cible.puissance if champ == "puissance" else cible.degats
                nom_cible = cible.template.nom
            elif type_effet == "degats":
                # Un malus de Degats frappe le TOTAL du duo adverse : pas de ciblage.
                cible = camp_adverse
                champ = "degats_camp"
                avant = camp_adverse.degats_bruts()
                nom_cible = f"duo de {camp_adverse.joueur.nom}"
            else:
                cible = source.cible
                if cible is None:
                    self.log.append(
                        f"{source.template.nom} Pouvoir ({pouvoir['description']}) : "
                        "aucune cible designee, effet perdu"
                    )
                    return
                champ = "puissance"
                avant = cible.puissance
                nom_cible = cible.template.nom
            if self._appliquer(source, cible, champ, valeur, label):
                self.log.append(
                    f"{source.template.nom} Pouvoir ({pouvoir['description']}) -> "
                    f"{champ} de {nom_cible} : {avant} -> {avant + valeur}"
                )

        elif type_effet == "stop_pouvoir":
            cible = source.cible
            if cible is None:
                self.log.append(f"{source.template.nom} Pouvoir : aucune cible designee")
                return
            if cible.camp.protege:
                self.log.append(
                    f"{source.template.nom} Pouvoir tente d'annuler le Pouvoir de "
                    f"{cible.template.nom}, bloque par la Protection de son camp"
                )
                return
            if cible.pouvoir() is None:
                self.log.append(
                    f"{source.template.nom} Pouvoir : {cible.template.nom} n'a aucun Pouvoir a annuler"
                )
                return
            if self._annuler_pouvoir(cible):
                self.log.append(
                    f"{source.template.nom} Pouvoir annule (retroactivement) le Pouvoir de "
                    f"{cible.template.nom}"
                )
            else:
                self.log.append(
                    f"{source.template.nom} Pouvoir annule par avance le Pouvoir de "
                    f"{cible.template.nom}"
                )

        elif type_effet == "copie_pouvoir":
            cible = source.cible
            if cible is None:
                self.log.append(f"{source.template.nom} Pouvoir : aucune cible designee")
                return
            pouvoir_copie = cible.pouvoir()
            if pouvoir_copie is None:
                self.log.append(
                    f"{source.template.nom} Pouvoir : {cible.template.nom} n'a aucun Pouvoir a copier"
                )
                return
            if cible.camp.protege:
                self.log.append(
                    f"{source.template.nom} Pouvoir tente de copier le Pouvoir de "
                    f"{cible.template.nom}, bloque par la Protection de son camp"
                )
                return
            if cible.stoppe:
                self.log.append(
                    f"{source.template.nom} Pouvoir : le Pouvoir de {cible.template.nom} "
                    "est deja annule, rien a copier"
                )
                return
            if _est_differee(pouvoir_copie):
                # Simplification POC : copier un Pouvoir conditionne par l'issue de la
                # bataille (Victoire/Defaite/Surpuissance) ou par Contrecoup n'est pas supporte.
                self.log.append(
                    f"{source.template.nom} Pouvoir : copie du Pouvoir de {cible.template.nom} "
                    "ignoree (Pouvoir conditionne par l'issue de la bataille, non supporte)"
                )
                return
            if _contient_copie_pouvoir(pouvoir_copie):
                # Recursion infinie : la cible designee ne change jamais d'une copie a l'autre.
                self.log.append(
                    f"{source.template.nom} Pouvoir : copie du Pouvoir de {cible.template.nom} "
                    "ignoree (Pouvoir qui copie lui-meme un Pouvoir, non supporte)"
                )
                return
            self.log.append(
                f"{source.template.nom} Pouvoir copie le Pouvoir de {cible.template.nom} "
                f"({pouvoir_copie['description']})"
            )
            if _verifier_condition(pouvoir_copie, source):
                # Le Pouvoir copie s'execute du point de vue du copieur, et ses effets a
                # cible unique visent la meme cible que celle designee pour la copie.
                label_copie = f"Pouvoir {source.template.nom} (copie de {cible.template.nom})"
                for effet_copie in pouvoir_copie["effets"]:
                    self._resoudre_effet(source, pouvoir_copie, effet_copie, label=label_copie)
            else:
                self.log.append(
                    f"{source.template.nom} Pouvoir copie : condition non remplie de son cote"
                )

        elif type_effet == "protection":
            camp.protege = True
            annules = self._nettoyer_effets_adverses(camp)
            suffixe = f", annule {annules} modification(s) subie(s)" if annules else ""
            self.log.append(
                f"{source.template.nom} Pouvoir (Protection) protege le camp "
                f"{camp.joueur.nom}{suffixe}"
            )

        elif type_effet == "echange":
            cible = source.cible
            if cible is None:
                self.log.append(f"{source.template.nom} Pouvoir : aucune cible designee")
                return
            if cible.camp.protege:
                self.log.append(
                    f"{source.template.nom} Pouvoir (Echange) bloque par la Protection du "
                    f"camp {cible.camp.joueur.nom}"
                )
                return
            # Les deltas sont calcules AVANT toute mutation, pour que l'echange reste
            # tracable dans le ledger (donc annulable par un Stop pouvoir retroactif)
            # plutot qu'une permutation directe non tracee.
            label_echange = f"Echange (Pouvoir {source.template.nom})"
            delta_puissance = cible.puissance - source.puissance
            delta_degats = cible.degats - source.degats
            self._appliquer(source, source, "puissance", delta_puissance, label_echange)
            self._appliquer(source, cible, "puissance", -delta_puissance, label_echange)
            self._appliquer(source, source, "degats", delta_degats, label_echange)
            self._appliquer(source, cible, "degats", -delta_degats, label_echange)
            self.log.append(
                f"{source.template.nom} Pouvoir echange Puissance/Degats avec {cible.template.nom}"
            )

        elif type_effet == "vampirisme":
            valeur = _valeur_effective(effet.get("valeur", 0), pouvoir, source)
            if camp_adverse.protege:
                self.log.append(
                    f"{source.template.nom} Pouvoir (Vampirisme {valeur}) bloque par la "
                    f"Protection du camp {camp_adverse.joueur.nom}"
                )
                return
            label_vampirisme = f"Pouvoir {source.template.nom} (Vampirisme)"
            self._appliquer(source, camp_adverse, "pv", -valeur, label_vampirisme)
            self._appliquer(source, camp, "pv", valeur, label_vampirisme)
            self.log.append(
                f"{source.template.nom} Pouvoir (Vampirisme {valeur}) : "
                f"{camp_adverse.joueur.nom} -{valeur} PV, {camp.joueur.nom} +{valeur} PV"
            )

    def _resoudre_pouvoir(self, source, differe):
        pouvoir = source.pouvoir()
        if pouvoir is None:
            return
        if _est_differee(pouvoir) != differe:
            return
        if source.stoppe:
            self.log.append(f"{source.template.nom} Pouvoir est annule, ignore")
            return
        if not _verifier_condition(pouvoir, source):
            self.log.append(
                f"{source.template.nom} Pouvoir ({pouvoir['description']}) : condition non remplie"
            )
            return
        for effet in pouvoir["effets"]:
            self._resoudre_effet(source, pouvoir, effet)

    # -------------------------------------------------------------- resolution
    def resoudre(self):
        # Pass 1 : Pouvoirs immediats, camp J1 (dans l'ordre du duo) puis camp J2.
        for camp in (self.camp_j1, self.camp_j2):
            for combattant in camp.combattants:
                self._resoudre_pouvoir(combattant, differe=False)

        puissance_j1 = self.camp_j1.puissance_totale()
        puissance_j2 = self.camp_j2.puissance_totale()
        self.camp_j1.puissance_figee = puissance_j1
        self.camp_j2.puissance_figee = puissance_j2
        if puissance_j1 > puissance_j2:
            self.camp_j1.gagnant = True
        elif puissance_j2 > puissance_j1:
            self.camp_j2.gagnant = True
        else:
            self.camp_j1.gagnant = True
            self.camp_j2.gagnant = True
            self.log.append(
                f"Egalite de Puissance ({puissance_j1} contre {puissance_j2}) : double victoire"
            )

        # Pass 2 : Pouvoirs differes (Victoire / Defaite / Surpuissance / Contrecoup).
        for camp in (self.camp_j1, self.camp_j2):
            for combattant in camp.combattants:
                self._resoudre_pouvoir(combattant, differe=True)

        # Bonus de Degats accorde au(x) vainqueur(s) par la carte bataille du tour.
        if self.bonus_degats_vainqueur:
            for camp in (self.camp_j1, self.camp_j2):
                if camp.gagnant:
                    camp.bonus_degats += self.bonus_degats_vainqueur
                    camp.detail_degats_camp.append(
                        ("carte bataille", self.bonus_degats_vainqueur)
                    )

        # Application des Degats du/des camp(s) vainqueur(s).
        for camp in (self.camp_j1, self.camp_j2):
            if not camp.gagnant:
                continue
            adverse = camp.adversaire
            degats = camp.degats_totaux()
            adverse.joueur.pv -= degats
            detail = [
                (c.template.nom, max(0, c.degats)) for c in camp.combattants
            ] + camp.detail_degats_camp
            if degats != camp.degats_bruts():
                # Les malus adverses ont fait passer le total sous 0 : le plancher
                # apparait dans le detail pour que la somme affichee reste exacte.
                detail.append(("plancher 0", degats - camp.degats_bruts()))
            self.log.append(
                f"Le duo de {camp.joueur.nom} remporte la bataille, Degats = "
                f"{_formater_detail(degats, detail)} : inflige {degats} a "
                f"{adverse.joueur.nom} (PV restants : {adverse.joueur.pv})"
            )

        return {
            "log": self.log,
            "camps": {
                self.camp_j1.joueur.nom: self.camp_j1.to_dict(),
                self.camp_j2.joueur.nom: self.camp_j2.to_dict(),
            },
            "gagnants": [
                camp.joueur.nom for camp in (self.camp_j1, self.camp_j2) if camp.gagnant
            ],
        }


def resoudre_bataille(camp_j1, camp_j2, tour, tours_max, bonus_degats_vainqueur=0):
    moteur = MoteurBataille(camp_j1, camp_j2, tour, tours_max, bonus_degats_vainqueur)
    return moteur.resoudre()
