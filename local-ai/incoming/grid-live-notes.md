# Grid: LA-7 live-data notes (2026-10-19)

Steps are in `local-ai/incoming/grid-live.txt` (lint: 0 problems). One chain, `LA7-GRID`, 16 steps, covers R4-GR-10, R4-GR-13 and R4-PG-14 (the 17 mapped reference plants). Data is frozen in `games/grid/data/`, rebuilt by `games/grid/tools/fetch_*.py`, checked by `games/grid/tests/test_*_snapshot.py`.

## What was frozen
| Item | File | Source and endpoint | CORS (checked 2026-10-19) | Counts |
|------|------|---------------------|---------------------------|--------|
| R4-GR-10 | `data/capacity_factors.json` | U.S. EIA, Electric Power Monthly Tables 6.07.A and 6.07.B (HTML pages, `epm_table_grapher.php?t=epmt_6_07_a` and `_b`) | none, so a dated snapshot (the EIA API needs a key) | 17 technologies, 10 annual rows each (2016 to 2025), data for July 2026 |
| R4-GR-13 | `data/solar_learning_curve.json` | Our World in Data, "Solar photovoltaic module prices vs. cumulative capacity" (IRENA 2025, Nemet, Farmer and Lafond): `https://ourworldindata.org/grapher/solar-pv-prices-vs-cumulative-capacity.csv` | `access-control-allow-origin: *`, so the page reads it live | 50 yearly rows 1975 to 2024 (2025 has capacity but no price and is left out) |
| R4-PG-11 | `data/moon_facts.json` | NASA NSSDCA Moon Fact Sheet (`nssdc.gsfc.nasa.gov/planetary/factsheet/moonfact.html`, page updated 2024-01-11) | none, snapshot | 12 values: synodic period 29.53 days, sidereal rotation 655.720 hours, gravity, irradiance, day and night temperature extremes and more |
| R4-PG-14 | `data/reference_plants.json` | EIA / Sargent and Lundy, Capital Cost and Performance Characteristic Estimates for Utility Scale Electric Power Generating Technologies (AEO2025), Table 1-2, PDF read with a stdlib reader | none, snapshot | 19 plants (capacity, heat rate, capital cost, fixed and variable O&M) |

## A list (`[local AI: in steps]`)
- R4-GR-10: steps 1 to 5 (reader helper, data functions, markup, render and boot loading, browser test). The table shows each plant's game nameplate beside the real average share of nameplate (EIA 2025 capacity factors, for example solar PV 24.4%).
- R4-GR-13: steps 6 to 12. A table and a small SVG of the real module price against the cost of your own solar plants per doubling of solar built. The real curve is read live from Our World in Data and falls back quietly to the dated snapshot; the source line says "read live on <date>" or "a dated snapshot read on <date>".
- R4-PG-14: steps 13 to 16, but only the 17 EIA plants that map onto Grid's plant types (coal, gas, nuclear, solar, wind, hydro, battery); geothermal and biomass-with-capture have no Grid plant, so they are not cards. A card unlocks when you have ever built a plant of its type.

## C list (not for the local AI)
| Item | Label | Reason |
|------|-------|--------|
| R4-PG-14 (the other 23 of 40 "components") | `[needs you]` | EIA's data covers 19 whole generating plants, not components. Turbines, panels and transformers have no EIA table, so a 40-part catalogue has no open source for 23 entries. Decide: keep the 17 EIA plants (done in steps), or name another open source (NREL Annual Technology Baseline is a candidate, not checked). |
| R4-PG-11 Moon base scenario | `[Claude: design]` | The snapshot is ready (day 29.53 days, so about 14.8 days of night is the game's own half: 29.53 / 2, not a NASA number). Turning that into a scenario needs a new entry in `SCENARIOS`, a night cycle for solar and wind, and balance, which is design work in `grid_rules.py` and the state files. |

## Notes for the Claude who audits
- Each step that adds markup also lists `pc-config.json` and says not to edit `pc.html`: after the audit run `scripts/generate-pc-pages.py`; `shared/tests/test_pc_games.py` fails until `pc.html` is regenerated (new element ids).
- `index.html` has about 4,700 bytes of room under its 16,500-token cap (`tests/test_file_sizes.py`); the three panels add about 1,000 bytes together.
- The data files are fetched at runtime and the service worker caches them after the first visit; add them to `offline-manifest.json` if you want them available on the very first offline visit.
- Re-running `tools/fetch_*.py` rewrites the JSON; the steps' tests read values from the JSON, never hard-code them.
- Mapping Grid plants to EIA technologies (gas = combined cycle) is the game's own choice, written in `CAPACITY_FACTOR_LABEL` in step 2.
