# CodingIsANoyvj — Game Demo Hub

A personal portfolio site collecting small AI-assisted game demos, all running client-side in the browser via Python/Pyodide — no build step, no backend required to play. Live, public, and updated regularly.

One demo, **SOL**, is also a dual BCM114/BCM206 university digital artefact — the site's public availability and update history serve as the evidence for that coursework requirement.

## What's here

- **SOL** — a solar-system incremental clicker.
- **Eight climate games** (Canopy, Grid, Tide, Aftermath, Herd, Thaw, Loop, Drift) — each a small, self-contained demo built around a distinct real-world climate mechanic, made for BCM114 Part 1. Every game includes an optional in-game "The Real Story" panel citing the real sources behind its mechanic.
- **Trade Empire** — a larger-scope logistics/economy game, built as a personal stretch project (not coursework).

Every game keeps its own `CLAUDE.md` documenting its concept, milestones, and design decisions in `games/<slug>/`.

## Stack

- Python via Pyodide (WebAssembly, runs in-browser) for game logic, plain HTML/CSS for structure and style — no build step anywhere.
- A small FastAPI + Postgres (Neon) backend (`app/`) for the shared star-rating/feedback widget and the save-code system.
- Static hosting, a PWA shell (installable, works offline once visited), and a labeled ad bar.

## Running locally

Any static file server works — for example:

```bash
python3 -m http.server 8073
```

Then open `http://localhost:8073`.

## Tests

Each game has its own pytest suite (a fake-DOM/Pyodide harness runs `game.py` headlessly under plain CPython):

```bash
cd games/<slug> && python3 -m pytest
```

The backend has its own suite too:

```bash
cd app && python3 -m pytest
```
