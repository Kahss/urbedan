"""Serveur Flask : sert le frontend statique et expose l'API REST du jeu."""
import os

from flask import Flask, jsonify, request, send_from_directory

from engine.game import ErreurPartie, Partie, charger_combattants

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "..", "data", "combattants.json")
FRONTEND_DIR = os.path.join(BASE_DIR, "..", "frontend")

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")

TEMPLATES = charger_combattants(DATA_PATH)

# Etat de jeu en memoire : une seule partie active a la fois (POC solo local).
partie = None


@app.get("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.get("/api/combattants")
def api_combattants():
    return jsonify([t.to_dict() for t in TEMPLATES.values()])


@app.post("/api/partie")
def api_nouvelle_partie():
    global partie
    body = request.get_json(force=True) or {}
    equipe = body.get("equipe", [])
    try:
        # Recharge les combattants a chaque nouvelle partie pour prendre en compte
        # une edition manuelle de data/combattants.json sans redemarrer le serveur.
        templates = charger_combattants(DATA_PATH)
        partie = Partie(templates, equipe)
    except ErreurPartie as e:
        return jsonify({"erreur": str(e)}), 400
    return jsonify(partie.etat_dict())


@app.get("/api/partie")
def api_etat_partie():
    if partie is None:
        return jsonify({"erreur": "Aucune partie en cours"}), 404
    return jsonify(partie.etat_dict())


@app.post("/api/partie/combattant")
def api_choix_combattant():
    if partie is None:
        return jsonify({"erreur": "Aucune partie en cours"}), 404
    body = request.get_json(force=True) or {}
    try:
        etat = partie.soumettre_combattant(body.get("combattant_id"))
    except ErreurPartie as e:
        return jsonify({"erreur": str(e)}), 400
    return jsonify(etat)


@app.post("/api/partie/pioche")
def api_decider_pioche():
    if partie is None:
        return jsonify({"erreur": "Aucune partie en cours"}), 404
    body = request.get_json(force=True) or {}
    try:
        etat = partie.decider_pioche(body.get("action"))
    except ErreurPartie as e:
        return jsonify({"erreur": str(e)}), 400
    return jsonify(etat)


@app.post("/api/partie/suivant")
def api_duel_suivant():
    if partie is None:
        return jsonify({"erreur": "Aucune partie en cours"}), 404
    try:
        etat = partie.duel_suivant()
    except ErreurPartie as e:
        return jsonify({"erreur": str(e)}), 400
    return jsonify(etat)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
