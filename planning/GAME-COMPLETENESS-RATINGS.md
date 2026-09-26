# Game Completeness Ratings

How "finished" each game feels, 1-5, and how that sets the length of each game's list in an ideas sheet. **Re-rate every time a new ideas sheet is generated** (user rule, 2026-09-26). We never stop working on a game — the rating only decides how much *new-idea* effort it gets.

| Rating | Meaning | Ideas per game (default) | Fallback if the sheet gets unmanageable |
|---|---|---|---|
| 1 | Could use a ton of work | 30 | 30 |
| 2 | Clearly unfinished in places | 25 | 20 |
| 3 | Solid core, real gaps | 20 | 10 |
| 4 | Nearly there, polish/extras | 15 | 5 |
| 5 | Basically nothing it needs | 5 | 2 |

## Ratings as of 2026-09-26

Basis: how much of the game's own TODO section is done (open/done counts from `planning/TODO.md` on this date), what the user's own audit flagged, and structural gaps (replay value, core-loop clarity). It is a judgment call, not a formula — change any number you disagree with.

| Game | Rating | Ideas | Open / done in TODO | Why |
|---|---|---|---|---|
| SOL | 4 | 15 | 2 / 28 | Deepest, most polished game (prestige/NG+, 24 achievements). Its main weak spot is the flat "fund research 20 times" loop (U10) plus a hold-to-click option (U11). |
| Canopy | 4 | 15 | 2 / 27 | Complete teaching game with legacy forest, biomes-lite and a full report card. Open: a third biome (B1) and a guided demo run (B29). |
| Grid | 4 | 15 | 3 / 26 | Career, scenarios, emergency mode, storage arbitrage all built. Open: the shadow-grid twin (C21), multi-grid (C3), real-region data (C29). |
| Tide | 4 | 15 | 2 / 26 | Managed retreat, storms, heritage, scenarios, checkpoint replay. Open: community seawall stats (D9) and the sister settlement (D3). |
| Aftermath | 3 | 20 | 7 / 23 | Best meta-progression on the hub, but the run structure has the most unbuilt modes (scenario packs E17a/b, curriculum E19, mentor E27, societal memory E29). |
| Herd | 4 | 15 | 4 / 25 | Second herd type, certification, biogas all in. Open: satellite farm (F1), succession (F25), two community items. |
| Thaw | 2 | 25 | 11 / 17 | The lightest of the climate games: the most unbuilt mechanics (carbon bank, cascade, rescue, archive, forecast mini-game, long game…). |
| Loop | 2 | 25 | 11 / 21 | Sound core, but eleven open mechanics (supply-chain redesign, lifecycle vignettes, passport, two challenge modes, richer visuals). |
| Drift | 3 | 20 | 6 / 24 | Good depth already; open: second region (I1), policy toolkit (I3), regional network (I7), second wave (I25), cross-region learning (I29). |
| Trade Empire | 3 | 20 | 3 / 26 | Full endgame, but the Z7 audit found no meta-progression at all (J21) and the map has room for a fourth cluster (J1) and guild contracts (J3). |
| Continuum | 3 | 20 | 1 / 30 | Feature-complete on paper (7 eras, 3D, dashboards), but the audit says its core pacing is confusing (U1, tick-based), era 8 is unbuilt (R2-K26), and it is the heaviest to load (U14). |
| Le Champ de Mots | 2 | 25 | 13 / 17 | A working SRS study tool with four arcade games, but the most open items on the hub (conversation sim, listening, phrasebook, cram mode, streak calendar, placement test…). |

**Totals with the default mapping:** 5 games at 4 (75) + 4 games at 3 (80) + 3 games at 2 (75) = **230 ideas per sheet per-game sections**, down from 360 at a flat 30 each. With the fallback mapping it would be 5×5 + 4×10 + 3×20 = 125.

No game is currently a 1 (nothing is that unfinished) or a 5 (every game has open items and audit findings).

## How it is used

1. When generating a new ideas sheet, read this file first, re-rate each game (open-item counts, new user audit findings, anything that shipped), update the table, then size each game's list from the mapping.
2. The non-per-game sections (new-game ideas, cross-game Z, hub Y, Warframe X) keep their own sizes.
3. If the resulting sheet is still too long to answer comfortably, switch to the fallback column and note that here.
