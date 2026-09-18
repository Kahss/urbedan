"""Cablage partage par les scripts d'analyse/simulation : chemins du projet (et
ajout de backend/ au sys.path pour pouvoir importer `engine.*`), et petits
helpers de reporting (progression console, ecriture CSV) repetés a l'identique
dans chacun d'eux."""
import csv
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "backend"))

DATA_PATH = os.path.join(PROJECT_ROOT, "data", "combattants.json")


def progression(i_apres, total, label, divisions=10):
    """Affiche sur stderr une ligne de progression environ `divisions` fois au
    cours d'une boucle de `total` iterations (silencieux le reste du temps)."""
    palier = max(1, total // divisions)
    if i_apres % palier == 0:
        print(f"... {label} : {i_apres}/{total}", file=sys.stderr)


def ecrire_csv(chemin, header, rows):
    with open(chemin, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
