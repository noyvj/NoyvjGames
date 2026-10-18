# Thaw: LA-7 live-data notes (2026-10-19)

Steps are in `local-ai/incoming/thaw-live.txt` (lint: 0 problems), one chain `LA7-THAW` of 5 steps for R4-PT-4. Data: `games/thaw/data/ice_cores.json`, rebuilt by `games/thaw/tools/fetch_ice_cores.py`, tested by `tests/test_ice_cores_snapshot.py`.

## What was frozen
NOAA NCEI / World Data Service for Paleoclimatology, Paleo Search API (`https://www.ncei.noaa.gov/access/paleo-search/study/search.json?searchText=ice%20core&limit=1000&skip=<n>`, `access-control-allow-origin: *`). Study type "ICE CORES" only. 30 cores, one per era, from a dataset spanning 357 years before 1950 (ITASE 02-4, Antarctica) to 801,662 years (EPICA Dome C). Each entry has site, place, latitude, longitude, elevation, core length when NOAA gives it, the dataset's oldest and newest age, study name, NOAA study id and link, DOI, investigators and the first publication citation.

Honest limits: the API's "ice core" search lists 47 usable single-site datasets whose title states a span that agrees with NOAA's record (multi-core and composite studies, caves, ice patches and sea-floor cores were left out because their span does not belong to one core), so the 30 are not evenly spread: there is a gap between 15,000 and 46,000 years. The age shown is the span of the named NOAA dataset, which can be shorter than the whole core (for example the Vostok and GRIP entries); the cards must say "dataset", as the steps do.

## A list (`[local AI: in steps]`)
R4-PT-4 as text rows inside the existing Climate archive panel (no new panel): 30 rows, locked rows show "???", the summary shows percent found. Default unlock rule (the owner may change it): the n-th core opens when your furthest round in any region reaches n + 1, read from the existing `climate_archive`, so no new save key is needed.

## C list
| Item | Label | Reason |
|------|-------|--------|
| R4-PT-4 live read | `[Claude: shared]` | One NOAA study can be read live with `...search.json?NOAAStudyId=<id>`, but some responses are very large, so the steps keep the dated snapshot and say so on screen. A live read of the chosen study only (when a row opens) would be a small JS hook; it needs a size decision first. |
| R4-PT-4 unlock rule | `[needs you]` | The item gives none ("a collection to complete"). The default above is a placeholder: round counts depend on how long a Thaw run really is. |

## For the Claude who audits
`index.html` has about 2,400 bytes of room under its 15,000-token cap; `pc.html` needs regenerating (the archive panel is already a window, so no config change).
