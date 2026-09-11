"""Moteur generique de resolution des Pouvoirs, pilote par les mots-cles de pouvoirs.csv.

Hypotheses de resolution retenues pour ce POC (voir README.md) :
- Chaque Combattant ne possede plus qu'un seul Pouvoir, et il est desormais toujours
  actif (version "stop ou encore" : il n'y a plus d'Energie determinant son
  activation). Le modificateur `par_carte` multiplie la valeur de l'effet par le
  nombre de Cartes Puissance piochees par le Combattant lui-meme ce duel-ci (plafonne
  par `plafond_cartes`, defaut 3). `par_carte_adverse` multiplie par le nombre de
  cartes piochees par l'adversaire, et `par_carte_en_jeu` par la somme des deux
  (soi + adversaire), avec le meme plafond.
- Un duel se resout en 2 passes : Pass 1 (pouvoir "immediat"), puis determination du
  vainqueur, puis Pass 2 (pouvoir conditionne par Victoire / Defaite, ou modificateur
  Contrecoup).
- Au sein de chaque passe, le Combattant J1 resout son Pouvoir actif avant que le
  Combattant J2 ne resolve le sien.
- Stop pouvoir et Copie pouvoir sont generiques : ils visent toujours l'unique Pouvoir
  de l'adversaire (toujours actif). Stop pouvoir agit retroactivement si ce pouvoir a
  deja ete resolu (cas ou le defenseur J2 vise le pouvoir de J1, deja joue), ou
  preventivement sinon (cas ou J1 vise le pouvoir de J2 qui n'a pas encore joue).
- Protection annule toutes les modifications deja subies de la part de l'adversaire et
  bloque toute nouvelle modification adverse (puissance/degats/vie/stop/copie) pour le
  reste de la resolution du duel.
- Patience/Impatience ne comptent pas le duel courant : Patience multiplie par le nombre
  de duels deja joues avant celui-ci (0 a 3), Impatience par le nombre de duels restants
  apres celui-ci (0 a 3), independamment des cartes piochees.
- Le detail du calcul de la Puissance/des Degats de chaque Combattant (base, cartes
  piochees, contribution du Pouvoir) est trace et restitue (`detail_puissance`,
  `detail_degats`, `puissance_txt`, `degats_txt`) pour affichage transparent.
"""


def _formater_detail(total, detail):
    morceaux = []
    for i, (label, valeur) in enumerate(detail):
        if i == 0:
            morceaux.append(f"{valeur} ({label})")
        else:
            signe = "+" if valeur >= 0 else "-"
            morceaux.append(f"{signe} {abs(valeur)} ({label})")
    return f"{total} = " + " ".join(morceaux)


PLAFOND_CARTES_PAR_DEFAUT = 3


class DuelCombattant:
    def __init__(self, joueur, instance, cartes, role, duel_numero, duels_max,
                 victoire_precedente=False, defaite_precedente=False):
        self.joueur = joueur
        self.instance = instance
        self.template = instance.template
        self.cartes = cartes
        self.nb_cartes = len(cartes)
        self.malus_total = sum(c.malus for c in cartes)
        busted = self.malus_total >= 3
        puissance_cartes = 0 if busted else sum(c.puissance for c in cartes)
        self.role = role  # "J1" ou "J2"
        self.duel_numero = duel_numero
        self.duels_max = duels_max
        self.victoire_precedente = victoire_precedente  # duel precedent gagne (False au duel 1)
        self.defaite_precedente = defaite_precedente  # duel precedent perdu (False au duel 1)
        self.puissance = self.template.puissance + puissance_cartes
        self.degats = self.template.degats
        self.detail_puissance = [("base", self.template.puissance), ("cartes piochees", puissance_cartes)]
        self.detail_degats = [("base", self.template.degats)]
        self.stoppe = False
        self.protege = False
        self.gagnant = False
        self.adversaire = None

    def pouvoir_actif(self):
        """Retourne le Pouvoir du Combattant : toujours actif dans cette version."""
        return self.template.pouvoir

    def recalculer_cartes(self):
        """Recalcule malus_total/puissance a partir de l'etat courant de `self.cartes`,
        et repercute la difference sur `self.puissance`/`detail_puissance`. Utilise par
        les effets qui redefinissent la Puissance/le Malus de certaines Cartes Puissance
        piochees (annule_type_carte, annule_premiere_carte_type, transforme_carte_type)."""
        self.malus_total = sum(c.malus for c in self.cartes)
        busted = self.malus_total >= 3
        puissance_cartes = 0 if busted else sum(c.puissance for c in self.cartes)
        for i, (label, valeur) in enumerate(self.detail_puissance):
            if label == "cartes piochees":
                delta = puissance_cartes - valeur
                if delta != 0:
                    self.puissance += delta
                    self.detail_puissance[i] = (label, puissance_cartes)
                break


def _valeur_effective(valeur, pouvoir, source):
    mod = pouvoir.get("modificateur")
    plafond = pouvoir.get("plafond_cartes", PLAFOND_CARTES_PAR_DEFAUT)
    if mod == "par_carte":
        return valeur * min(source.nb_cartes, plafond)
    if mod == "par_carte_adverse":
        return valeur * min(source.adversaire.nb_cartes, plafond)
    if mod == "par_carte_en_jeu":
        return valeur * min(source.nb_cartes + source.adversaire.nb_cartes, plafond)
    if mod == "patience":
        return valeur * (source.duel_numero - 1)
    if mod == "impatience":
        return valeur * (source.duels_max - source.duel_numero)
    if mod == "par_niveau_adverse":
        return valeur * source.adversaire.template.niveau
    return valeur


def _verifier_condition(condition, source):
    if condition is None:
        return True
    adv = source.adversaire
    if condition == "courage":
        return source.role == "J1"
    if condition == "riposte":
        return source.role == "J2"
    if condition == "vengeance":
        return adv.joueur.pv > source.joueur.pv
    if condition == "domination":
        return adv.joueur.pv < source.joueur.pv
    if condition == "victoire":
        return source.gagnant
    if condition == "defaite":
        return not source.gagnant
    if condition == "surcharge":
        return source.malus_total >= 3
    if condition == "surcharge_adverse":
        return adv.malus_total >= 3
    if condition == "degats_adverse_3+":
        return adv.template.degats >= 3
    if condition == "plus_cartes_adverse":
        return adv.nb_cartes > source.nb_cartes
    if condition == "victoire_precedente":
        return source.victoire_precedente
    if condition == "defaite_precedente":
        return source.defaite_precedente
    if condition.endswith("+") and condition[:-1].isdigit():
        return source.nb_cartes >= int(condition[:-1])
    return True


def _est_differee(pouvoir):
    return pouvoir.get("condition") in ("victoire", "defaite") or pouvoir.get("modificateur") == "contrecoup"


def _contient_copie_pouvoir(pouvoir):
    return any(effet["type"] == "copie_pouvoir" for effet in pouvoir.get("effets", []))


class MoteurDuel:
    def __init__(self, dc1, dc2):
        self.dc1 = dc1
        self.dc2 = dc2
        dc1.adversaire = dc2
        dc2.adversaire = dc1
        self.ledger = []  # {source, cible, champ, valeur}
        self.log = []

    def _appliquer(self, source, cible, champ, valeur, label):
        if valeur == 0:
            return True
        if cible is not source and cible.protege:
            self.log.append(
                f"{source.template.nom} (Pouvoir) est bloque par la Protection de {cible.template.nom}"
            )
            return False
        detail_liste = None
        if champ == "puissance":
            cible.puissance += valeur
            detail_liste = cible.detail_puissance
        elif champ == "degats":
            cible.degats += valeur
            detail_liste = cible.detail_degats
        elif champ == "pv":
            cible.joueur.pv += valeur
        detail_entree = None
        if detail_liste is not None:
            detail_entree = (label, valeur)
            detail_liste.append(detail_entree)
        self.ledger.append({
            "source": source, "cible": cible, "champ": champ, "valeur": valeur,
            "detail_liste": detail_liste, "detail_entree": detail_entree,
        })
        return True

    def _annuler_pouvoir(self, cible):
        """Annule le Pouvoir du Combattant `cible` : revert de tous les effets deja
        produits par ce pouvoir, qu'il ait porte sur lui-meme ou sur l'adversaire."""
        cible.stoppe = True
        restants = []
        annule = False
        for record in self.ledger:
            if record["source"] is cible:
                self._revert(record)
                annule = True
            else:
                restants.append(record)
        self.ledger = restants
        return annule

    def _revert(self, record):
        cible, champ, valeur = record["cible"], record["champ"], record["valeur"]
        if champ == "puissance":
            cible.puissance -= valeur
        elif champ == "degats":
            cible.degats -= valeur
        elif champ == "pv":
            cible.joueur.pv -= valeur
        if record["detail_liste"] is not None and record["detail_entree"] in record["detail_liste"]:
            record["detail_liste"].remove(record["detail_entree"])

    def _nettoyer_effets_adverses(self, cible):
        restants = []
        annules = 0
        for record in self.ledger:
            if record["cible"] is cible and record["source"] is not cible:
                self._revert(record)
                annules += 1
            else:
                restants.append(record)
        self.ledger = restants
        return annules

    def _resoudre_effet(self, source, pouvoir, effet, label=None):
        adv = source.adversaire
        t = effet["type"]
        mod = pouvoir.get("modificateur")
        label = label or f"Pouvoir {source.template.nom}"

        if t in ("puissance", "degats", "vie"):
            champ = "pv" if t == "vie" else t
            cible = source if effet.get("cible", "soi") == "soi" else adv
            if mod == "contrecoup" and not source.gagnant:
                self.log.append(
                    f"{source.template.nom} Pouvoir ({pouvoir['description']}) : Contrecoup non declenche (pas de victoire)"
                )
                return
            valeur = _valeur_effective(effet.get("valeur", 0), pouvoir, source)
            avant = cible.puissance if champ == "puissance" else (cible.degats if champ == "degats" else cible.joueur.pv)
            applique = self._appliquer(source, cible, champ, valeur, label)
            if applique:
                cible_nom = cible.template.nom if champ != "pv" else cible.joueur.nom
                self.log.append(
                    f"{source.template.nom} Pouvoir ({pouvoir['description']}) -> "
                    f"{champ} de {cible_nom} : {avant} -> {avant + valeur}"
                )

        elif t == "stop_pouvoir":
            # Generique : vise toujours l'unique Pouvoir de l'adversaire, s'il est actif.
            pouvoir_adv = adv.pouvoir_actif()
            if pouvoir_adv is None:
                self.log.append(
                    f"{source.template.nom} Pouvoir : {adv.template.nom} n'a active aucun Pouvoir a annuler"
                )
                return
            if adv.protege:
                self.log.append(
                    f"{source.template.nom} Pouvoir tente d'annuler le Pouvoir de {adv.template.nom}, bloque par Protection"
                )
                return
            annule = self._annuler_pouvoir(adv)
            if annule:
                self.log.append(
                    f"{source.template.nom} Pouvoir annule (retroactivement) le Pouvoir de {adv.template.nom}"
                )
            else:
                self.log.append(
                    f"{source.template.nom} Pouvoir annule par avance le Pouvoir de {adv.template.nom}"
                )

        elif t == "copie_pouvoir":
            # Generique : copie toujours l'unique Pouvoir de l'adversaire, s'il est actif.
            pouvoir_copie = adv.pouvoir_actif()
            if pouvoir_copie is None:
                self.log.append(
                    f"{source.template.nom} Pouvoir : {adv.template.nom} n'a active aucun Pouvoir a copier"
                )
                return
            if adv.protege:
                self.log.append(
                    f"{source.template.nom} Pouvoir tente de copier le Pouvoir de {adv.template.nom}, bloque par Protection"
                )
                return
            if adv.stoppe:
                self.log.append(
                    f"{source.template.nom} Pouvoir : le Pouvoir de {adv.template.nom} est deja annule, rien a copier"
                )
                return
            if _est_differee(pouvoir_copie):
                # Simplification POC : copier un pouvoir conditionne par l'issue du duel
                # (Victoire/Defaite) ou par Contrecoup n'est pas supporte.
                self.log.append(
                    f"{source.template.nom} Pouvoir : copie du Pouvoir de {adv.template.nom} ignoree "
                    "(pouvoir conditionne par l'issue du duel, non supporte)"
                )
                return
            if _contient_copie_pouvoir(pouvoir_copie):
                # Copier un Pouvoir qui contient lui-meme une Copie de pouvoir provoquerait une
                # recursion infinie (l'adversaire cible ne change jamais d'une copie a l'autre) :
                # non supporte, comme les autres limitations POC de Copie pouvoir.
                self.log.append(
                    f"{source.template.nom} Pouvoir : copie du Pouvoir de {adv.template.nom} ignoree "
                    "(pouvoir qui copie lui-meme un Pouvoir, non supporte)"
                )
                return
            self.log.append(
                f"{source.template.nom} Pouvoir copie le Pouvoir de {adv.template.nom} ({pouvoir_copie['description']})"
            )
            if _verifier_condition(pouvoir_copie.get("condition"), source):
                label_copie = f"Pouvoir {source.template.nom} (copie de {adv.template.nom})"
                for e2 in pouvoir_copie["effets"]:
                    self._resoudre_effet(source, pouvoir_copie, e2, label=label_copie)

        elif t == "protection":
            source.protege = True
            annules = self._nettoyer_effets_adverses(source)
            suffixe = f", annule {annules} modification(s) subie(s)" if annules else ""
            self.log.append(f"{source.template.nom} Pouvoir (Protection) active{suffixe}")

        elif t == "echange":
            if adv.protege:
                self.log.append(
                    f"{source.template.nom} Pouvoir (Echange) bloque par Protection de {adv.template.nom}"
                )
                return
            # Calcule les deltas a partir des valeurs de BASE (template), pas des totaux
            # courants : seules les stats imprimees sur la carte s'echangent, les cartes
            # Puissance piochees et les effets de Pouvoir deja appliques restent a leur
            # combattant d'origine. Applique comme un delta (plutot qu'une permutation
            # directe) pour que l'effet reste tracable et reversible par un Stop pouvoir
            # retroactif, via le meme ledger que les autres effets.
            label_echange = f"Echange (Pouvoir {source.template.nom})"
            delta_puissance = adv.template.puissance - source.template.puissance
            delta_degats = adv.template.degats - source.template.degats
            self._appliquer(source, source, "puissance", delta_puissance, label_echange)
            self._appliquer(source, adv, "puissance", -delta_puissance, label_echange)
            self._appliquer(source, source, "degats", delta_degats, label_echange)
            self._appliquer(source, adv, "degats", -delta_degats, label_echange)
            self.log.append(
                f"{source.template.nom} Pouvoir echange Puissance/Degats avec {adv.template.nom}"
            )

        elif t == "vampirisme":
            x = _valeur_effective(effet.get("valeur", 0), pouvoir, source)
            if adv.protege:
                self.log.append(
                    f"{source.template.nom} Pouvoir (Vampirisme {x}) bloque par Protection de {adv.template.nom}"
                )
                return
            label_vampirisme = f"Pouvoir {source.template.nom} (Vampirisme)"
            self._appliquer(source, adv, "pv", -x, label_vampirisme)
            self._appliquer(source, source, "pv", x, label_vampirisme)
            self.log.append(
                f"{source.template.nom} Pouvoir (Vampirisme {x}) : {adv.joueur.nom} {-x} PV, {source.joueur.nom} +{x} PV"
            )

        elif t in ("annule_type_carte", "annule_premiere_carte_type"):
            # Neutralise (puissance=0, malus=0) une ou toutes les Cartes Puissance d'un
            # type donne, deja piochees par la cible (par defaut l'adversaire). Modifie
            # directement les cartes (non revertible par un Stop pouvoir retroactif :
            # limitation POC, comme les autres cas non geres de Copie/Stop pouvoir).
            cible = source if effet.get("cible", "adversaire") == "soi" else adv
            if cible.protege:
                self.log.append(
                    f"{source.template.nom} Pouvoir tente d'annuler des cartes {effet['carte_type']} de "
                    f"{cible.template.nom}, bloque par Protection"
                )
                return
            type_vise = effet["carte_type"]
            candidates = [c for c in cible.cartes if c.nom == type_vise and (c.puissance != 0 or c.malus != 0)]
            touchees = candidates if t == "annule_type_carte" else candidates[:1]
            if not touchees:
                self.log.append(
                    f"{source.template.nom} Pouvoir : {cible.template.nom} n'a pioche aucune carte "
                    f"{type_vise} a annuler"
                )
                return
            for c in touchees:
                c.puissance = 0
                c.malus = 0
            cible.recalculer_cartes()
            self.log.append(
                f"{source.template.nom} Pouvoir annule {len(touchees)} carte(s) {type_vise} de {cible.template.nom}"
            )

        elif t == "transforme_carte_type":
            # Redefinit la Puissance/le Malus des Cartes Puissance d'un type donne,
            # piochees par la cible (par defaut soi-meme).
            cible = adv if effet.get("cible", "soi") == "adversaire" else source
            type_vise = effet["carte_type"]
            nouvelle_puissance = effet.get("puissance", 0)
            nouveau_malus = effet.get("malus", 0)
            touchees = [c for c in cible.cartes if c.nom == type_vise]
            if not touchees:
                self.log.append(
                    f"{source.template.nom} Pouvoir : {cible.template.nom} n'a pioche aucune carte "
                    f"{type_vise} a transformer"
                )
                return
            for c in touchees:
                c.puissance = nouvelle_puissance
                c.malus = nouveau_malus
            cible.recalculer_cartes()
            self.log.append(
                f"{source.template.nom} Pouvoir transforme {len(touchees)} carte(s) {type_vise} de "
                f"{cible.template.nom} en {nouvelle_puissance}/{nouveau_malus}"
            )

        elif t == "carte_cachee_premiere":
            # Effet purement informationnel (masque la premiere Carte Puissance piochee
            # par l'adversaire aux yeux du joueur humain) : applique par la Partie
            # (game.py) au moment de la pioche, pas de valeur chiffree ici.
            self.log.append(
                f"{source.template.nom} Pouvoir : la premiere Carte Puissance piochee par "
                f"{adv.template.nom} reste face cachee"
            )

    def _resoudre_pouvoir(self, source, differe):
        """Resout l'unique Pouvoir de `source` (toujours actif) si sa nature
        (immediat/differe) correspond a la passe en cours. Chaque effet peut porter sa
        propre `condition`, qui prevaut sur celle du Pouvoir pour cet effet uniquement
        (permet par exemple de combiner une Protection inconditionnelle avec un second
        effet conditionne, au sein d'un seul et meme Pouvoir)."""
        pouvoir = source.pouvoir_actif()
        if pouvoir is None:
            return
        if _est_differee(pouvoir) != differe:
            return
        if source.stoppe:
            self.log.append(f"{source.template.nom} Pouvoir est annule, ignore")
            return
        condition_globale = pouvoir.get("condition")
        resolu = False
        for effet in pouvoir["effets"]:
            if not _verifier_condition(effet.get("condition", condition_globale), source):
                continue
            self._resoudre_effet(source, pouvoir, effet)
            resolu = True
        if not resolu:
            self.log.append(
                f"{source.template.nom} Pouvoir ({pouvoir['description']}) : condition non remplie"
            )

    def resoudre(self):
        # Pass 1 : pouvoir immediat, J1 puis J2 (chacun n'a qu'un seul Pouvoir). Execute
        # avant le constat de surcharge ci-dessous, car un Pouvoir immediat peut modifier
        # les Cartes Puissance piochees (transforme_carte_type, annule_type_carte, ...)
        # et donc changer le Malus total final.
        for combattant in (self.dc1, self.dc2):
            self._resoudre_pouvoir(combattant, differe=False)

        for combattant in (self.dc1, self.dc2):
            if combattant.malus_total >= 3:
                self.log.append(
                    f"{combattant.template.nom} : Malus total {combattant.malus_total} >= 3, "
                    "puissance des cartes piochees annulee (puissance de base conservee)"
                )

        if self.dc1.puissance > self.dc2.puissance:
            self.dc1.gagnant = True
        elif self.dc2.puissance > self.dc1.puissance:
            self.dc2.gagnant = True
        else:
            self.dc1.gagnant = True
            self.dc2.gagnant = True
            self.log.append("Egalite de Puissance : double victoire")

        # Pass 2 : pouvoir differe (Victoire / Defaite / Contrecoup)
        for combattant in (self.dc1, self.dc2):
            self._resoudre_pouvoir(combattant, differe=True)

        # Application des degats du/des vainqueur(s)
        for combattant in (self.dc1, self.dc2):
            if combattant.gagnant:
                adv = combattant.adversaire
                degats = max(0, combattant.degats)
                adv.joueur.pv -= degats
                self.log.append(
                    f"{combattant.template.nom} remporte le duel, Degats = "
                    f"{_formater_detail(combattant.degats, combattant.detail_degats)} : "
                    f"inflige {degats} a {adv.joueur.nom} (PV restants : {adv.joueur.pv})"
                )

        return {
            "log": self.log,
            "gagnants": [c.template.nom for c in (self.dc1, self.dc2) if c.gagnant],
            "gagnants_ids": [c.template.id for c in (self.dc1, self.dc2) if c.gagnant],
            "puissance_finale": {self.dc1.template.nom: self.dc1.puissance, self.dc2.template.nom: self.dc2.puissance},
            "degats_finale": {self.dc1.template.nom: self.dc1.degats, self.dc2.template.nom: self.dc2.degats},
            "detail_puissance": {
                self.dc1.template.nom: self.dc1.detail_puissance,
                self.dc2.template.nom: self.dc2.detail_puissance,
            },
            "detail_degats": {
                self.dc1.template.nom: self.dc1.detail_degats,
                self.dc2.template.nom: self.dc2.detail_degats,
            },
            "puissance_txt": {
                self.dc1.template.nom: _formater_detail(self.dc1.puissance, self.dc1.detail_puissance),
                self.dc2.template.nom: _formater_detail(self.dc2.puissance, self.dc2.detail_puissance),
            },
            "degats_txt": {
                self.dc1.template.nom: _formater_detail(self.dc1.degats, self.dc1.detail_degats),
                self.dc2.template.nom: _formater_detail(self.dc2.degats, self.dc2.detail_degats),
            },
        }


def resoudre_duel(joueur_j1, combattant_j1, cartes_j1, joueur_j2, combattant_j2, cartes_j2, duel_numero, duels_max=4,
                   victoire_precedente_j1=False, defaite_precedente_j1=False,
                   victoire_precedente_j2=False, defaite_precedente_j2=False):
    dc1 = DuelCombattant(joueur_j1, combattant_j1, cartes_j1, "J1", duel_numero, duels_max,
                          victoire_precedente_j1, defaite_precedente_j1)
    dc2 = DuelCombattant(joueur_j2, combattant_j2, cartes_j2, "J2", duel_numero, duels_max,
                          victoire_precedente_j2, defaite_precedente_j2)
    moteur = MoteurDuel(dc1, dc2)
    return moteur.resoudre()
