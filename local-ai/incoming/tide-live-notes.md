# Tide: LA-7 live-data notes (2026-10-19)

Steps are in `local-ai/incoming/tide-live.txt` (lint: 0 problems), one chain `LA7-TIDE` of 3 steps for R4-TI-11. Data: `games/tide/data/sea_level_pathways.json` (`tools/fetch_sea_level.py`, `tests/test_sea_level_snapshot.py`) and `games/tide/data/specimens.json` (`tools/fetch_specimens.py`, `tests/test_specimens_snapshot.py`).

## What was frozen
| Item | File | Source | CORS | Counts |
|------|------|--------|------|--------|
| R4-TI-11 | `sea_level_pathways.json` | IPCC AR6 Working Group I, Chapter 9, Table 9.9 (global mean sea level, five SSP scenarios plus the SSP5-8.5 low-confidence column; medians with likely ranges, relative to 1995 to 2014), parsed from `https://www.ipcc.ch/report/ar6/wg1/chapter/chapter-9/` | none on the 2 MB page, so a dated snapshot | 12 rows x 6 scenarios: five components for 2100, totals for 2030, 2050, 2090, 2100, 2150, and two rates. For example SSP1-2.6 2100: 0.44 m (0.32 to 0.62), SSP5-8.5: 0.77 m (0.63 to 1.01) |
| R4-PI-3 | `specimens.json` | WoRMS REST API (`marinespecies.org/rest`: accepted name, taxonomy, common names, "Body size" entries with their references) and the first two sentences of each Wikipedia summary | `*` for both | 24 deep-water species, all accepted names; 16 have a WoRMS body size (the sizes in WoRMS can disagree, for example the vampire squid lists 40 cm and 20 mm, so the file keeps every entry with its reference) |

## A list (`[local AI: in steps]`)
R4-TI-11: a note under the existing scenario picker that pairs the game's Conservative, Moderate and Severe scenarios with SSP1-2.6, SSP2-4.5 and SSP5-8.5 and prints the IPCC median and likely range for 2100, with the source and "a dated snapshot read on <date>". The pairing is the game's own choice. The note says the game's per-season rise is a simpler scale; no game number changes. The IPCC page has no CORS header, so this cannot be live.

## C list (not for the local AI)
| Item | Label | Reason |
|------|-------|--------|
| R4-PI-3 Specimen Jars | `[Claude: design]` | The data and facts are ready (24 species, with WoRMS taxonomy and a Wikipedia sentence pair each, live-readable). What is missing is design: which ocean change makes which creature "appear", the jar-on-a-shelf collection view (art), and the count (the item names none). |
| R4-TI-11 numbers into play | `[needs you]` | If the scenarios should really follow IPCC values (for example 0.44, 0.56 and 0.77 m by 2100) the three `rise` numbers in `SEA_SCENARIOS` would change, which moves the core balance tests. The steps leave them alone. |

## For the Claude who audits
- `index.html` has about 1,000 bytes under its 16,000-token cap; the step adds about 60.
- `pc.html` is generated: run `scripts/generate-pc-pages.py`.
