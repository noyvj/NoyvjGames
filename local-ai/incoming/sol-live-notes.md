# SOL: LA-7 live-data notes (2026-10-19)

Steps are in `local-ai/incoming/sol-live.txt` (lint: 0 problems), one chain `LA7-SOL` of 6 steps for the text-card part of R4-PS-2. Data: `games/sol/data/wonders.json` (rebuilt by `games/sol/tools/fetch_wonders.py`, tested by `tests/test_wonders_snapshot.py`) and `games/sol/data/transfer_data.json` (`tools/fetch_transfer_data.py`, `tests/test_transfer_data_snapshot.py`).

## What was frozen
| Item | File | Source | CORS | Counts |
|------|------|--------|------|--------|
| R4-PS-2 | `wonders.json` | NASA Science (`science.nasa.gov`), page summaries through its public WordPress REST API: `https://science.nasa.gov/wp-json/wp/v2/<topic or posts>?slug=<slug>&_fields=title,link,excerpt,modified` | answers `access-control-allow-origin` with the asking origin (checked with `https://noyvj.github.io`), so a live read works | 41 sights in all 8 worlds: Earth 3, Moon 4, Mars 9, Venus 1, Asteroid Belt 6, Pluto 6, Jupiter's moons 6, Saturn's moons 6. Each fact is NASA's own excerpt copied exactly; 12 end with NASA's own cut marker, flagged `cut_short` |
| R4-PS-26 | `transfer_data.json` | NASA JPL Solar System Dynamics: Astrodynamic Parameters, Approximate Positions of the Planets (Table 1), Planetary Physical Parameters, the Small-Body Database API (Ceres, Pluto) and Planetary Satellite Mean Elements | none on any of them, snapshot | Sun GM and the astronomical unit; semi-major axis and period for Venus, Earth, Mars, Jupiter, Saturn, Ceres (stands for the Asteroid Belt), Pluto; the Moon's orbit around Earth |

The target was "about 40 sights": 41 reached. Venus has only one (Maxwell Montes) because the NASA pages found for Maat Mons and others carried only image-release text, not a fact.

## A list (`[local AI: in steps]`)
R4-PS-2, the text part only: a "Wonders" section in the Charter panel (built from Python, so no `index.html` change), a saved lifetime list `wonders_found` (written only when not empty), a toast when one is found, and the dated NASA fact on each found card. Default unlock rule (the owner may change it): the n-th wonder of a world appears with your n-th Auto-Miner on that world. A found wonder never leaves the list.

## C list (not for the local AI)
| Item | Label | Reason |
|------|-------|--------|
| R4-PS-2 low-poly cards | `[Claude: art]` | "A small low-poly card" for each sight is art. The text cards in the steps are the placeholder; the art needs a style decision and, in SOL, `index.html` has only about 870 bytes under its 21,500-token cap (the earlier `sol-notes.md` already spends most of it). |
| R4-PS-2 live NASA read | `[Claude: shared]` | The facts are frozen; a live read per found wonder is possible (each entry has its `api` URL) but SOL builds the Charter from Python on a signature change, so a live refresh needs a small JS hook plus a decision on how many requests to allow. The cards say "a dated snapshot". |
| R4-PS-26 transfer windows | `[Claude: design]` | The fuel-and-timing puzzle needs design: what a "window" costs, how fuel is priced against the existing trade routes, and where it sits in `sol_actions.py` and `sol_econ.py`. The numbers are ready: orbit sizes and periods from JPL. The synodic periods and Hohmann transfer times are the game's own arithmetic from those numbers (the file does not store them). |

## For the Claude who audits
- Run the whole `games/sol` suite: `tests/test_charter.py` and `tests/test_save_system.py` touch the Charter and save keys.
- The earlier `sol.txt` chains also edit `sol_savestate.py` and `index.html`: expect small merge conflicts.
