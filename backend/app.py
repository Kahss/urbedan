"""Serveur Flask : sert le frontend statique et expose l'API REST du jeu (Eredice)."""
import os

from flask import Flask, jsonify, request, send_from_directory

from engine.game import ErreurPartie, Partie
from engine.models import charger_personnages

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "..", "data", "personnages.json")
FRONTEND_DIR = os.path.join(BASE_DIR, "..", "frontend")

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")

# Etat de jeu en memoire : une seule partie active a la fois (POC solo local).
partie = None


@app.get("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.get("/api/personnages")
def api_personnages():
    return jsonify([t.to_dict() for t in charger_personnages(DATA_PATH).values()])


@app.post("/api/partie")
def api_nouvelle_partie():
    global partie
    body = request.get_json(force=True) or {}
    try:
        # Recharge les Personnages a chaque nouvelle partie, pour prendre en compte une
        # edition manuelle de data/personnages.json sans redemarrer le serveur.
        partie = Partie(charger_personnages(DATA_PATH), body.get("equipe", []))
    except ErreurPartie as e:
        return jsonify({"erreur": str(e)}), 400
    return jsonify(partie.etat_dict())


@app.get("/api/partie")
def api_etat_partie():
    if partie is None:
        return jsonify({"erreur": "Aucune partie en cours"}), 404
    return jsonify(partie.etat_dict())


@app.post("/api/partie/draft")
def api_draft():
    if partie is None:
        return jsonify({"erreur": "Aucune partie en cours"}), 404
    body = request.get_json(force=True) or {}
    try:
        etat = partie.drafter(
            body.get("de_id"), body.get("personnage_id"), body.get("usage"),
        )
    except ErreurPartie as e:
        return jsonify({"erreur": str(e)}), 400
    return jsonify(etat)


@app.post("/api/partie/choix")
def api_choix_capacite():
    """Tranche le choix du joueur quand plusieurs Capacites d'un meme Personnage sont
    payables en meme temps : la cascade d'activations reprend ensuite son cours."""
    if partie is None:
        return jsonify({"erreur": "Aucune partie en cours"}), 404
    body = request.get_json(force=True) or {}
    try:
        etat = partie.choisir_capacite(body.get("indice"))
    except ErreurPartie as e:
        return jsonify({"erreur": str(e)}), 400
    return jsonify(etat)


@app.post("/api/partie/ia")
def api_creneau_ia():
    """Resout un seul creneau de l'IA. Le frontend appelle cette route en boucle tant que
    `joueur_courant` vaut "ia", ce qui lui permet d'animer chaque choix separement."""
    if partie is None:
        return jsonify({"erreur": "Aucune partie en cours"}), 404
    try:
        etat = partie.jouer_creneau_ia()
    except ErreurPartie as e:
        return jsonify({"erreur": str(e)}), 400
    return jsonify(etat)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
