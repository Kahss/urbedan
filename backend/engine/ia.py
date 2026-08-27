"""Heuristique de choix de l'IA : quel Combattant engager.

- **Combattant** : tire au hasard parmi ceux encore disponibles. L'IA ne contre-choisit
  pas le Combattant adverse (cf. instructions.md).

La revelation des cartes Bataille est automatique (pioche unique, sans choix), l'IA n'a
donc plus de decision a y prendre.
"""
import random


def choisir_combattant(joueur):
    """Choisit au hasard un Combattant parmi ceux qui n'ont pas encore combattu."""
    return random.choice(joueur.combattants_disponibles())
