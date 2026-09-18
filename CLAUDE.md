# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A playable solo (vs AI) prototype of the tabletop game **Urban Eredan** (rules in `game.md`): a Python/Flask backend (rules engine + AI) and a vanilla HTML/CSS/JS frontend (click-only, no framework). Cards are mostly plain text, but each Combattant now has a small icon (`image` field in the JSON, served from `img/` via `GET /img/<path>`) — the original "no illustrations" design intent from `instructions.md` has since evolved.

Several alternative rule sets were explored during design (`versions/*.md`); the one actually implemented is `versions/stop_ou_encore.md` ("stop or go again" draw mechanic). `README.md` documents the implementation in detail (data model, power keyword semantics, AI heuristics, resolution order) — read it before making engine changes, it's the primary spec.

The current branch is mid-refactor of the draw/bust mechanic (see `git status`/`git diff`): moving from "auto-bust at 3 Malus" (README's documented behavior) towards a "draw freely + fold (`se coucher`)" mechanic where accumulated Malus costs PV directly unless you fold. `backend/test_pioche_couche.py` documents/asserts the new intended behavior — when it conflicts with `README.md`, the code and this test are more current than the README for that specific mechanic.

## Running the game

Dependencies are managed with `uv` (`pyproject.toml` + `uv.lock`, Python >=3.14, `.venv/` already present).

```bash
uv run backend/app.py          # starts Flask on http://127.0.0.1:5000/
```

Flask serves both the REST API (`/api/...`) and the static frontend (`frontend/`) from the same process. Game state is a single in-memory `Partie` (module-level global in `backend/app.py`) — one game at a time, no persistence, no concurrency handling (fine for local solo use, not fine to "fix" with multi-session support unless asked).

Note: `README.md`'s own run instructions reference a Windows `venv\Scripts\python.exe` + `backend/requirements.txt` setup that predates the `uv`/`pyproject.toml` setup now in place — prefer `uv run`.

## Analysis / simulation scripts

All live in `scripts/`, import the engine via `backend/`, and share `scripts/_bootstrap.py` (adds `backend/` to `sys.path`, resolves `data/combattants.json`, small progress/CSV helpers). Run them from the repo root with `uv run`:

```bash
uv run scripts/generate_metagame.py -n 10000   # AI-vs-AI simulation; win% per Combattant (balance signal)
uv run scripts/analyse_matchups.py             # matchup matrix/heatmap between Combattants
uv run scripts/analyse_coherence_rangs.py      # checks niveau (rank) vs actual win-rate coherence
uv run scripts/simulate_pioche_burst.py        # draw-phase-specific simulation
```

`backend/simulate_puissance.py` is a similar standalone simulation script at the backend root (not under `scripts/`).

## Tests

No test framework/runner — tests are small standalone `assert`-based scripts, run directly:

```bash
cd backend && python3 test_pioche_couche.py
```

Follow this pattern (plain functions named `test_*`, asserts with descriptive messages, run via `if __name__ == "__main__"`) for new engine tests rather than introducing pytest.

## Architecture

**Data flow**: `data/combattants.json` is the actual data the game loads (`engine.models.CombattantTemplate`, loaded by `engine.game.charger_combattants`). `data/Urban Eredan - Cartes - Combattants.csv` is a hand-edited spreadsheet export that is the *source of truth for design intent* but is NOT read by the game directly — it must be manually reconciled into the JSON (see `.claude/skills/sync-combattants/SKILL.md`, invoked as `/sync-combattants`). The JSON carries structured fields (`id`, `image`, `condition`, `modificateur`, `effets`) that the CSV doesn't have; never regenerate the JSON wholesale from the CSV.

**Backend layers** (`backend/engine/`):
- `models.py` — data classes: `CartePuissance` (draw deck cards), `CombattantTemplate` (static Combattant definition from JSON), `CombattantEnEquipe` (instance within a team, tracks `utilise`), `Joueur` (PV + team).
- `powers.py` — generic, data-driven power resolution engine. Powers are declared in JSON as `condition` + `modificateur` + `effets` (list of `{type, cible, valeur}`), not as per-character code. `_verifier_condition`/`_valeur_effective`/`_resoudre_effet` are the keyword dispatch tables — extending a power keyword means adding a branch here (and in `frontend/app.js` if it needs different display), never hardcoding a case for a specific Combattant id/name. Duels resolve in two passes: an "immediate" pass, then winner determination, then a second pass for Victoire/Defaite/Contrecoup-conditioned effects. Within each pass, J1's power resolves before J2's.
- `ia.py` — AI heuristics: `choisir_combattant` (pick the Combattant maximizing estimated duel power) and `decider_piocher_ou_arreter` (draw/stop decision based on exact expected value from the remaining known deck composition).
- `game.py` — orchestrates a `Partie` (team setup incl. `tirer_equipe_equilibree` for the AI's balanced random team, duel sequencing, AI turns). `NIVEAU_TOTAL_MAX = 8`: a team's 4 Combattants' `niveau` (1-3) must sum to ≤8 — enforced both at `Partie.__init__` (human team) and in `tirer_equipe_equilibree` (AI team); this same function is reused by `generate_metagame.py`.

**`backend/app.py`** is a thin REST layer over `Partie`: `GET /api/combattants` (reloads `combattants.json` on every call, so manual edits show up without restarting), `POST /api/partie` (new game), `GET /api/partie` (state), `POST /api/partie/combattant`, `POST /api/partie/pioche`, `POST /api/partie/suivant`, plus `GET /img/<path>` for Combattant icons. `ErreurPartie` exceptions become HTTP 400 via a Flask error handler; a `requiert_partie` decorator 404s routes when no game is active.

**Frontend** (`frontend/`) is one `index.html` + `app.js` + `style.css`, no build step, no framework — talks to the API with `fetch`. `frontend/app.js` is the place to mirror any new power-effect display logic added in `powers.py`.

## Adding/editing Combattants

See `README.md`'s "Editer / ajouter des Combattants" section for the full JSON schema of a power (`condition`, `modificateur`, `effets`, `plafond_cartes`). Two entry points:
- Spreadsheet was updated by the user → run `/sync-combattants` to reconcile CSV → JSON (and engine, if a genuinely new mechanic is needed).
- Designing a brand new character from a fictional description → use the `recruteur` subagent (`.claude/agents/recruteur.md`): it drafts 3 balanced designs, and validates a chosen one by running `generate_metagame.py` (target: 45-55% win rate for the new Combattant).
