"""Serveur Flask : sert le frontend statique et expose l'API REST du jeu."""
import functools
import os

from flask import Flask, jsonify, request, send_from_directory

from engine.game import ErreurPartie, Partie, charger_combattants

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "..", "data", "combattants.json")
FRONTEND_DIR = os.path.join(BASE_DIR, "..", "frontend")
IMG_DIR = os.path.join(BASE_DIR, "..", "img")

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")


@app.errorhandler(ErreurPartie)
def gerer_erreur_partie(e):
    return jsonify({"erreur": str(e)}), 400


@app.get("/img/<path:nom_fichier>")
def img_illustration(nom_fichier):
    return send_from_directory(IMG_DIR, nom_fichier)

# Etat de jeu en memoire : une seule partie active a la fois (POC solo local).
partie = None


def requiert_partie(vue):
    """Renvoie 404 si aucune partie n'est en cours, sans repeter la garde dans
    chaque route qui agit sur la partie active."""
    @functools.wraps(vue)
    def wrapper(*args, **kwargs):
        if partie is None:
            return jsonify({"erreur": "Aucune partie en cours"}), 404
        return vue(*args, **kwargs)
    return wrapper


@app.get("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.get("/api/combattants")
def api_combattants():
    # Recharge a chaque appel pour prendre en compte une edition manuelle de
    # data/combattants.json sans redemarrer le serveur (comme /api/partie).
    return jsonify([t.to_dict() for t in charger_combattants(DATA_PATH).values()])


@app.post("/api/partie")
def api_nouvelle_partie():
    global partie
    body = request.get_json(force=True) or {}
    equipe = body.get("equipe", [])
    templates = charger_combattants(DATA_PATH)
    partie = Partie(templates, equipe)
    return jsonify(partie.etat_dict())


@app.get("/api/partie")
@requiert_partie
def api_etat_partie():
    return jsonify(partie.etat_dict())


@app.post("/api/partie/combattant")
@requiert_partie
def api_choix_combattant():
    body = request.get_json(force=True) or {}
    etat = partie.soumettre_combattant(body.get("combattant_id"))
    return jsonify(etat)


@app.post("/api/partie/pioche")
@requiert_partie
def api_decider_pioche():
    body = request.get_json(force=True) or {}
    etat = partie.decider_pioche(body.get("action"))
    return jsonify(etat)


@app.post("/api/partie/suivant")
@requiert_partie
def api_duel_suivant():
    etat = partie.duel_suivant()
    return jsonify(etat)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
