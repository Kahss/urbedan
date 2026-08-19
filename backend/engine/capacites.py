"""Capacites des Combattants : chaque Combattant en porte une, qui lui permet d'influer
sur le cours de la partie (cf. `versions/battles.md`, section « Systeme de capacites »).

Une capacite se compose de trois parties :

- une **condition** (facultative) : quand la capacite s'active
- un **effet** (obligatoire) : ce qu'elle fait
- un **multiplicateur** (facultatif) : combien de fois l'effet est applique

Les effets se rangent en deux familles, qui ne s'appliquent pas au meme moment du duel :

- les **passifs** (`initiative`, `annule_couleur`) modifient la facon dont les batailles se
  resolvent : ils sont figes des que les deux Combattants sont engages, avant la premiere
  carte Bataille. Ils ne peuvent donc porter ni une condition qui depend de l'issue du duel
  (`victoire`, `defaite`), ni un multiplicateur (il n'y a rien a multiplier).
- les effets de **resolution** (`vampirisme`, PV, Degats) s'appliquent a la fin du duel, au
  moment ou le vainqueur inflige ses Degats : les modificateurs de Degats sont pris en
  compte avant que les Degats ne soient retires, puis les PV sont ajustes.
"""
from .batailles import CARAC_PAR_COULEUR, COULEUR_PAR_CARAC, LIBELLE_CARAC

# --- Conditions -------------------------------------------------------------------
# victoire / defaite : le Combattant doit remporter / perdre son duel
# premier / second   : le joueur doit etre J1 / J2 de ce duel
# vengeance          : le joueur doit avoir perdu son duel precedent
# confiance          : le joueur doit avoir remporte son duel precedent
CONDITIONS = ("victoire", "defaite", "premier", "second", "vengeance", "confiance")
# Ces deux-la ne sont connues qu'a la fin du duel : elles sont interdites aux passifs.
CONDITIONS_FIN_DE_DUEL = ("victoire", "defaite")

LIBELLE_CONDITION = {
    "victoire": "Victoire",
    "defaite": "Defaite",
    "premier": "Premier",
    "second": "Second",
    "vengeance": "Vengeance",
    "confiance": "Confiance",
}

# --- Effets -----------------------------------------------------------------------
# initiative     : le Combattant remporte les batailles que la condition ne tranche pas
# annule_couleur : la caracteristique de cette couleur tombe a 0 chez l'adversaire
EFFETS_PASSIFS = ("initiative", "annule_couleur")
# vampirisme     : l'adversaire perd X PV, le joueur en gagne X
# pv_soi         : le joueur gagne X PV
# pv_adverse     : l'adversaire perd X PV
# degats_soi     : les Degats du Combattant sont augmentes de X
# degats_adverse : les Degats du Combattant adverse sont diminues de X
EFFETS_RESOLUTION = ("vampirisme", "pv_soi", "pv_adverse", "degats_soi", "degats_adverse")
EFFETS = EFFETS_PASSIFS + EFFETS_RESOLUTION

# --- Multiplicateurs --------------------------------------------------------------
# patience               : x le nombre de duels joues, celui-ci compris
# impatience             : x le nombre de duels restant a jouer, celui-ci compris
# par_bataille_remportee : x le nombre de batailles remportees dans ce duel
# par_bataille_perdue    : x le nombre de batailles perdues dans ce duel
MULTIPLICATEURS = ("patience", "impatience", "par_bataille_remportee", "par_bataille_perdue")

LIBELLE_MULTIPLICATEUR = {
    "patience": "par duel joue",
    "impatience": "par duel restant",
    "par_bataille_remportee": "par bataille remportee",
    "par_bataille_perdue": "par bataille perdue",
}


class Effet:
    """L'effet d'une capacite : son type, sa valeur (X) et, pour `annule_couleur`, la
    couleur visee."""

    def __init__(self, data, nom_combattant):
        if not isinstance(data, dict):
            raise ValueError(f"{nom_combattant} : l'effet de la capacite doit etre un objet")
        self.type = data.get("type")
        if self.type not in EFFETS:
            raise ValueError(
                f"{nom_combattant} : effet de capacite inconnu '{self.type}' "
                f"(attendu parmi {', '.join(EFFETS)})"
            )
        self.valeur = data.get("valeur")
        self.couleur = data.get("couleur")

        if self.type == "annule_couleur":
            if self.couleur not in CARAC_PAR_COULEUR:
                raise ValueError(
                    f"{nom_combattant} : 'annule_couleur' exige une couleur parmi "
                    f"{', '.join(CARAC_PAR_COULEUR)}"
                )
        elif self.couleur is not None:
            raise ValueError(f"{nom_combattant} : l'effet '{self.type}' ne prend pas de couleur")

        if self.type in EFFETS_PASSIFS:
            if self.valeur is not None:
                raise ValueError(f"{nom_combattant} : l'effet '{self.type}' ne prend pas de valeur")
        elif not isinstance(self.valeur, int) or self.valeur < 1:
            raise ValueError(
                f"{nom_combattant} : l'effet '{self.type}' exige une valeur entiere >= 1"
            )

    @property
    def carac_annulee(self):
        return CARAC_PAR_COULEUR[self.couleur] if self.type == "annule_couleur" else None

    def libelle(self):
        if self.type == "initiative":
            return "Initiative"
        if self.type == "annule_couleur":
            return f"Annule la {LIBELLE_CARAC[self.carac_annulee]} adverse"
        if self.type == "vampirisme":
            return f"Vampirisme {self.valeur}"
        pluriel = self.valeur > 1
        unite = "PV" if self.type.startswith("pv") else ("Degats" if pluriel else "Degat")
        if self.type in ("pv_soi", "degats_soi"):
            return f"+{self.valeur} {unite}"
        return f"-{self.valeur} {unite} adverse" + ("s" if pluriel else "")

    def to_dict(self):
        return {"type": self.type, "valeur": self.valeur, "couleur": self.couleur}


class Capacite:
    """La capacite d'un Combattant, telle que decrite dans data/combattants.json."""

    def __init__(self, data, nom_combattant):
        if not isinstance(data, dict):
            raise ValueError(f"{nom_combattant} : la capacite doit etre un objet")
        inconnus = set(data) - {"condition", "effet", "multiplicateur"}
        if inconnus:
            raise ValueError(
                f"{nom_combattant} : champ(s) de capacite inconnu(s) : {', '.join(sorted(inconnus))}"
            )
        self.condition = data.get("condition")
        if self.condition is not None and self.condition not in CONDITIONS:
            raise ValueError(
                f"{nom_combattant} : condition de capacite inconnue '{self.condition}' "
                f"(attendu parmi {', '.join(CONDITIONS)})"
            )
        self.multiplicateur = data.get("multiplicateur")
        if self.multiplicateur is not None and self.multiplicateur not in MULTIPLICATEURS:
            raise ValueError(
                f"{nom_combattant} : multiplicateur de capacite inconnu '{self.multiplicateur}' "
                f"(attendu parmi {', '.join(MULTIPLICATEURS)})"
            )
        if "effet" not in data:
            raise ValueError(f"{nom_combattant} : une capacite doit porter un effet")
        self.effet = Effet(data["effet"], nom_combattant)

        # Un passif agit pendant les batailles : il doit etre connu avant la premiere carte
        # revelee, et il n'est pas quantitatif.
        if self.effet.type in EFFETS_PASSIFS:
            if self.condition in CONDITIONS_FIN_DE_DUEL:
                raise ValueError(
                    f"{nom_combattant} : l'effet '{self.effet.type}' agit pendant les batailles "
                    f"et ne peut pas dependre de l'issue du duel ('{self.condition}')"
                )
            if self.multiplicateur is not None:
                raise ValueError(
                    f"{nom_combattant} : l'effet '{self.effet.type}' n'est pas quantitatif et "
                    "n'accepte pas de multiplicateur"
                )

    @property
    def passive(self):
        """Vrai si la capacite agit pendant les batailles (et non a la resolution)."""
        return self.effet.type in EFFETS_PASSIFS

    def libelle(self):
        """Le texte de la capacite, tel qu'imprime sur la carte Combattant."""
        texte = self.effet.libelle()
        if self.multiplicateur:
            texte += " " + LIBELLE_MULTIPLICATEUR[self.multiplicateur]
        if self.condition:
            texte = f"{LIBELLE_CONDITION[self.condition]} : {texte}"
        return texte

    def to_dict(self):
        return {
            "libelle": self.libelle(),
            "condition": self.condition,
            "effet": self.effet.to_dict(),
            "multiplicateur": self.multiplicateur,
            "passive": self.passive,
        }


def charger_capacite(data, nom_combattant):
    """Construit la Capacite d'un Combattant ; `None` s'il n'en a pas."""
    if data is None:
        return None
    return Capacite(data, nom_combattant)


def vocabulaire():
    """Les mots cles disponibles pour ecrire une capacite, pour la legende du frontend."""
    return {
        "conditions": [
            {"cle": cle, "libelle": LIBELLE_CONDITION[cle], "texte": texte}
            for cle, texte in (
                ("victoire", "le Combattant doit remporter le duel"),
                ("defaite", "le Combattant doit perdre le duel"),
                ("premier", "le joueur doit etre J1 de ce duel"),
                ("second", "le joueur doit etre J2 de ce duel"),
                ("vengeance", "le joueur doit avoir perdu son duel precedent"),
                ("confiance", "le joueur doit avoir remporte son duel precedent"),
            )
        ],
        "effets": [
            {"cle": cle, "libelle": libelle, "texte": texte}
            for cle, libelle, texte in (
                ("vampirisme", "Vampirisme X",
                 "l'adversaire perd X PV, le joueur en gagne X"),
                ("pv_soi", "+X PV", "le joueur gagne X PV"),
                ("pv_adverse", "-X PV adverses", "l'adversaire perd X PV"),
                ("degats_soi", "+X Degats",
                 "les Degats du Combattant sont augmentes de X"),
                ("degats_adverse", "-X Degats adverses",
                 "les Degats du Combattant adverse sont diminues de X"),
                ("initiative", "Initiative",
                 "le Combattant remporte les batailles que la condition ne tranche pas"),
                ("annule_couleur", "Annule une couleur",
                 "la caracteristique de la couleur visee tombe a 0 chez l'adversaire pour "
                 "tout le duel"),
            )
        ],
        "multiplicateurs": [
            {
                "cle": cle,
                "libelle": cle.replace("_", " ").capitalize(),
                "texte": f"{LIBELLE_MULTIPLICATEUR[cle]} ({texte})",
            }
            for cle, texte in (
                ("patience", "le nombre de duels joues, celui-ci compris"),
                ("impatience", "le nombre de duels restants, celui-ci compris"),
                ("par_bataille_remportee", "les batailles remportees dans ce duel"),
                ("par_bataille_perdue", "les batailles perdues dans ce duel"),
            )
        ],
        "couleurs": [
            {"couleur": couleur, "carac": LIBELLE_CARAC[carac]}
            for carac, couleur in COULEUR_PAR_CARAC.items()
        ],
    }
