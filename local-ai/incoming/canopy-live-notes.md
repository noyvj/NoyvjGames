# Canopy: LA-7 live-data notes (2026-10-19)

Steps are in `local-ai/incoming/canopy-live.txt` (lint: 0 problems), one chain `LA7-CANOPY` of 8 steps for R4-CA-8 and R4-CA-14. Data in `games/canopy/data/`, rebuilt by `games/canopy/tools/fetch_forest_carbon.py`, `fetch_wildlife.py`, `fetch_region_losses.py`, tested by `tests/test_forest_carbon_snapshot.py`, `test_wildlife_status_snapshot.py`, `test_region_losses_snapshot.py`.

## What was frozen
| Item | File | Source | CORS | Counts |
|------|------|--------|------|--------|
| R4-CA-8 | `forest_carbon.json` | FAO Global Forest Resources Assessment 2020, Key findings (PDF `fao.org/3/ca8753en/ca8753en.pdf`): forests hold 662 Gt carbon, 163 t carbon per hectare in 2020 (159 in 1990), 4.06 billion ha; and Our World in Data, "Above-ground forest biomass" (FAO SDG 15.2.1, `ourworldindata.org/grapher/above-ground-biomass-in-forest-per-hectare.csv`) | PDF: none (snapshot). OWID CSV: `*` (live) | 4 FAO sentences kept verbatim, 13 OWID country or world values |
| R4-CA-14 (and the wildlife lists for R4-CA-4) | `wildlife_status.json` | IUCN Red List category as published through the GBIF species API (`api.gbif.org/v1/species/<key>/iucnRedListCategory`; the IUCN's own API needs a key), plus the first two sentences of each Wikipedia summary | `*` for both (live) | 20 species: 6 for the existing wildlife-log icons, 6 boreal, 8 tropical; all 20 have a category (Blue morpho is Not Evaluated) |
| R4-CA-4 | `region_losses.json` | Our World in Data, "Tree cover loss by dominant driver" (Global Forest Watch), `tree-cover-loss-by-dominant-driver.csv` | `*` (live) | 5 countries (Canada, Russia for boreal; Brazil, Indonesia, Democratic Republic of Congo for tropical), 24 years 2001 to 2024, 7 drivers |

## A list (`[local AI: in steps]`)
- R4-CA-8: steps 1 to 4. One plot counts as one hectare (a default, `HECTARES_PER_PLOT = 1`); the readout multiplies standing plots by FAO's 163 t carbon per hectare and by 44.01 / 12.011 for CO2. FAO's PDF cannot be read live, so the line says "a dated snapshot". The OWID biomass series is live-capable but measures biomass, not carbon, so it is kept in the file and not shown as carbon.
- R4-CA-14: steps 5 to 8. The six existing wildlife icons are generic (owl, fox, deer, frog, butterfly, woodpecker), so the file pairs each with a representative species (Tawny owl, Red fox, Red deer, Common frog, Monarch butterfly, Great spotted woodpecker); that pairing is a design choice for the owner. The status is read live from GBIF when the Wildlife log opens, with the snapshot as the quiet fallback. Caveat: the species-level Monarch is Least Concern in GBIF's IUCN data while its migratory populations are assessed separately as Endangered; the card would say Least Concern.

## C list (not for the local AI)
| Item | Label | Reason |
|------|-------|--------|
| R4-CA-4 two new regions | `[Claude: design]` | Two new playable grids need growth speeds, wildlife and a loss mechanic. The data side is ready: boreal and tropical wildlife lists with IUCN status, and the main cause of tree cover loss over 2015 to 2024 (computed from the yearly values in the file): Wildfire for Canada and Russia, Permanent agriculture for Brazil and Indonesia, Shifting cultivation for the Democratic Republic of Congo. These are whole-country figures, so the game must say "tree cover loss in Canada and Russia", not "in the boreal forest". No sourced "growth speed" exists in these datasets; growth rhythm is a design choice. Region mechanics (`canopy_regions.py`, `canopy_worldvars.py`, saves) are a big design change. |

## For the Claude who audits
- `index.html` is near its 15,000-token cap (about 1,000 bytes of room left): the steps add about 300 bytes in total; check `tests/test_file_sizes.py`.
- `pc.html` is generated: run `scripts/generate-pc-pages.py` after the markup steps.
