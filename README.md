# CodingIsANoyvj — Game Demo Hub

A personal portfolio site collecting small AI-assisted game demos, all running client-side in the browser via Python/Pyodide — no build step. Live, public, and updated regularly.

One demo, **SOL**, is also a dual BCM114/BCM206 university digital artefact — the site's public availability and update history serve as the evidence for that coursework requirement.

## What's here

- **SOL** — a solar-system incremental clicker. The reference integration for the shared save widget.
- **Eight climate games** (Canopy, Grid, Tide, Aftermath, Herd, Thaw, Loop, Drift) — each a small, self-contained demo built around a distinct real-world climate mechanic, made for BCM114 Part 1. Every game includes an optional in-game "The Real Story" panel citing the real sources behind its mechanic.
- **Le Champ de Mots** — a French-vocabulary spaced-repetition study tool, built as a personal project (not tied to any coursework).
- **Trade Empire** and **Continuum** — larger-scope personal stretch projects, both built but not yet linked from the hub.

Every game keeps its own `CLAUDE.md` documenting its concept, milestones, and design decisions in `games/<slug>/`.

## Stack

- Python via Pyodide (WebAssembly, runs in-browser) for game logic, plain HTML/CSS for structure and style — no build step anywhere.
- A small FastAPI + Postgres (Neon) backend (`app/`) for the star-rating/feedback widgets, username+password accounts, and the save-code system.
- `shared/save-widget.js` — one script, dropped unchanged into every game, handling save/load and (if signed in) autoloading the account's most recent save for that game. See `planning/SAVE-BUTTON-INTEGRATION.md`.
- Static hosting, a PWA shell (installable, works offline once visited), and a labeled ad bar.

Playing a game itself needs no backend; saving progress, accounts, and reviews do.

## Running locally

Any static file server works — for example:

```bash
python3 -m http.server 8073
```

Then open `http://localhost:8073`.

## Tests

Each game has its own pytest suite (a fake-DOM/Pyodide harness runs `game.py` headlessly under plain CPython) — run per game, not from the repo root (every game's `tests/conftest.py` shares the same module path, so a root-level `pytest` run fails to collect across games):

```bash
cd games/<slug> && python3 -m pytest
```

The backend has its own suite too:

```bash
cd app && python3 -m pytest
```
