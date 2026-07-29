"""Moteur generique de resolution des Pouvoirs, pilote par les mots-cles de pouvoirs.csv.

Hypotheses de resolution retenues pour ce POC (voir README.md) :
- Chaque Combattant ne possede plus qu'un seul Pouvoir. Ce Pouvoir peut definir un cout
  minimum en Energie (`energie_min`, note "X+") : il ne s'active que si l'Energie du
  Glyphe joue est superieure ou egale a ce seuil (`energie_min` absent ou 0 = Pouvoir
  toujours actif, quelle que soit l'Energie jouee, y compris 0). Le modificateur
  `par_energie` permet en plus de multiplier la valeur de l'effet par l'Energie
  effectivement jouee (ex : "+1 Puissance / Energie").
- Un duel se resout en 2 passes : Pass 1 (pouvoir "immediat"), puis determination du
  vainqueur, puis Pass 2 (pouvoir conditionne par Victoire / Defaite / Surpuissance, ou
  modificateur Contrecoup).
- Au sein de chaque passe, le Combattant J1 resout son Pouvoir actif avant que le
  Combattant J2 ne resolve le sien.
- Stop pouvoir et Copie pouvoir sont generiques : ils visent toujours l'unique Pouvoir
  de l'adversaire, s'il est actif (Energie jouee >= son seuil). Stop pouvoir agit
  retroactivement si ce pouvoir a deja ete resolu (cas ou le defenseur J2 vise le
  pouvoir de J1, deja joue), ou preventivement sinon (cas ou J1 vise le pouvoir de J2
  qui n'a pas encore joue).
- Protection annule toutes les modifications deja subies de la part de l'adversaire et
  bloque toute nouvelle modification adverse (puissance/degats/vie/stop/copie) pour le
  reste de la resolution du duel.
- Patience/Impatience se basent sur le numero du duel courant dans la partie (1 a 4),
  independamment de l'Energie jouee.
- Le detail du calcul de la Puissance/des Degats de chaque Combattant (base, Glyphe,
  contribution du Pouvoir) est trace et restitue (`detail_puissance`, `detail_degats`,
  `puissance_txt`, `degats_txt`) pour affichage transparent.
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


class DuelCombattant:
    def __init__(self, joueur, instance, glyphe, role, duel_numero, duels_max):
        self.joueur = joueur
        self.instance = instance
        self.template = instance.template
        self.glyphe = glyphe
        self.role = role  # "J1" ou "J2"
        self.duel_numero = duel_numero
        self.duels_max = duels_max
        self.puissance = self.template.puissance + glyphe.puissance
        self.degats = self.template.degats
        self.detail_puissance = [("base", self.template.puissance), ("glyphe", glyphe.puissance)]
        self.detail_degats = [("base", self.template.degats)]
        self.stoppe = False
        self.protege = False
        self.gagnant = False
        self.adversaire = None

    def pouvoir_actif(self):
        """Retourne le Pouvoir du Combattant s'il est active par l'Energie du Glyphe
        joue (>= energie_min du Pouvoir), sinon None."""
        pouvoir = self.template.pouvoir
        if pouvoir is None:
            return None
        if self.glyphe.energie < pouvoir.get("energie_min", 0):
            return None
        return pouvoir


def _valeur_effective(valeur, pouvoir, source):
    mod = pouvoir.get("modificateur")
    if mod == "par_energie":
        return valeur * source.glyphe.energie
    if mod == "patience":
        return valeur * source.duel_numero
    if mod == "impatience":
        return valeur * (source.duels_max - source.duel_numero + 1)
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
    if condition == "surpuissance":
        return source.gagnant and source.puissance >= 2 * adv.puissance
    return True


def _est_differee(pouvoir):
    return pouvoir.get("condition") in ("victoire", "defaite", "surpuissance") or pouvoir.get("modificateur") == "contrecoup"


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
            if mod == "contrecoup":
                if not source.gagnant:
                    self.log.append(
                        f"{source.template.nom} Pouvoir ({pouvoir['description']}) : Contrecoup non declenche (pas de victoire)"
                    )
                    return
                cible = source
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
                # (Victoire/Defaite/Surpuissance) ou par Contrecoup n'est pas supporte.
                self.log.append(
                    f"{source.template.nom} Pouvoir : copie du Pouvoir de {adv.template.nom} ignoree "
                    "(pouvoir conditionne par l'issue du duel, non supporte)"
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
            # Calcule les deltas AVANT toute mutation, pour que l'echange reste tracable
            # (et reversible par un Stop pouvoir retroactif) via le meme ledger que les
            # autres effets, plutot qu'une permutation directe non tracee.
            label_echange = f"Echange (Pouvoir {source.template.nom})"
            delta_puissance = adv.puissance - source.puissance
            delta_degats = adv.degats - source.degats
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

    def _resoudre_pouvoir(self, source, differe):
        """Resout l'unique Pouvoir de `source`, s'il est actif (Energie jouee >= son
        seuil) et si sa nature (immediat/differe) correspond a la passe en cours."""
        pouvoir = source.pouvoir_actif()
        if pouvoir is None:
            return
        if _est_differee(pouvoir) != differe:
            return
        if source.stoppe:
            self.log.append(f"{source.template.nom} Pouvoir est annule, ignore")
            return
        if not _verifier_condition(pouvoir.get("condition"), source):
            self.log.append(
                f"{source.template.nom} Pouvoir ({pouvoir['description']}) : condition non remplie"
            )
            return
        for effet in pouvoir["effets"]:
            self._resoudre_effet(source, pouvoir, effet)

    def resoudre(self):
        self.log.append(
            f"-- Glyphes reveles : {self.dc1.template.nom} joue {self.dc1.glyphe.notation_txt()} / "
            f"{self.dc2.template.nom} joue {self.dc2.glyphe.notation_txt()} --"
        )
        # Pass 1 : pouvoir immediat, J1 puis J2 (chacun n'a qu'un seul Pouvoir)
        for combattant in (self.dc1, self.dc2):
            self._resoudre_pouvoir(combattant, differe=False)

        self.log.append(
            f"Puissance totale {self.dc1.template.nom} : "
            f"{_formater_detail(self.dc1.puissance, self.dc1.detail_puissance)}"
        )
        self.log.append(
            f"Puissance totale {self.dc2.template.nom} : "
            f"{_formater_detail(self.dc2.puissance, self.dc2.detail_puissance)}"
        )
        if self.dc1.puissance > self.dc2.puissance:
            self.dc1.gagnant = True
        elif self.dc2.puissance > self.dc1.puissance:
            self.dc2.gagnant = True
        else:
            self.dc1.gagnant = True
            self.dc2.gagnant = True
            self.log.append("Egalite de Puissance : double victoire")

        # Pass 2 : pouvoir differe (Victoire / Defaite / Surpuissance / Contrecoup)
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


def resoudre_duel(joueur_j1, combattant_j1, glyphe_j1, joueur_j2, combattant_j2, glyphe_j2, duel_numero, duels_max=4):
    dc1 = DuelCombattant(joueur_j1, combattant_j1, glyphe_j1, "J1", duel_numero, duels_max)
    dc2 = DuelCombattant(joueur_j2, combattant_j2, glyphe_j2, "J2", duel_numero, duels_max)
    moteur = MoteurDuel(dc1, dc2)
    return moteur.resoudre()
