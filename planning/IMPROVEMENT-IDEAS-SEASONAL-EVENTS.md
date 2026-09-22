# Improvement Ideas — Seasonal/Real-World-Date Events (Z23 seed)

Seeded from `planning/TODO.md` item **Z23**: a lightweight shared mechanism for a game to show different flavor text/art on real-world dates — explicitly **event-based** (a week-long "holiday" tied to a real calendar date, not a palette swap), the way you framed it in `IMPROVEMENT-IDEAS-ROUND-2.md`'s `## Z` answers: *"a 'holiday' lasts a week and something like christmas they have to play canopy in a mode for getting christmas trees to get the 'christmas 2026' badge on their profile."*

This document does **not** build anything. It's a brainstorm of concrete per-game event ideas plus a design sketch for the shared mechanism's shape, so that whenever you pick which ones (if any) you actually want, real per-game TODO checklist items can be written straight from your picks instead of starting from a blank page. Z23 itself stays unchecked in `TODO.md` until that happens.

**Games covered:** the 8 climate-quartet games (Canopy, Grid, Tide, Aftermath, Herd, Thaw, Loop, Drift) each have an obvious real-world-date tie-in, so all 8 get at least one idea. SOL and Le Champ de Mots each get one idea that fits their own theme instead of forcing a climate angle. Trade Empire and Continuum are skipped — per Z23's own scoping note, neither has a natural "climate holiday" hook, and nothing here should read as pressure to invent one.

Every idea below follows the same shape the badge system already has zero-backend-cost precedent for (per `CLAUDE.md`'s Site-level milestone 8, achievements ride the existing save/account system with no backend changes) — a real-world date window, a flavor-only change to existing UI/text, and a reward that's a badge or a small cosmetic, never a new balanced mechanic.

Letters below match the same per-game lettering used in `IMPROVEMENT-IDEAS-ROUND-2.md`/`-ROUND-3.md`, so cross-referencing is easy.

---

## A. SOL

1. **New Year "New Horizons" nudge.** Window: Dec 31 – Jan 6. SOL's own hope-angle is expansion/growth, and prestige/NG+ is already the closest thing it has to a "turn over a new leaf" moment. During the window, the main screen shows a one-line seasonal banner ("A new year, a new system — ready to go again?") next to the Prestige button, and starting a prestige run (or, if the "New Game+" idea from Round 2's A3 ever gets built, starting one of those) during the window grants a **"New Horizons 2027"** profile badge. No numeric bonus — it's a nudge to do a thing players can already do, timed to a real calendar moment, exactly the "opt-in flavor, not a new system" shape Z23 asks for.

---

## B. Canopy

1. **Christmas "Holiday Tree-Planting Drive"** — the exact case from your own Round 2 answer, written up concretely. Window: Dec 20–27. Forest-request flavor text swaps to holiday-themed asks ("a family wants a tree for the town square this Christmas," "the ranger station wants a windbreak planted before the holidays"), and the Replant button gets a small string/color reskin (e.g. a subtle string of lights on the plot icon) for the week — cosmetic only, no cost change, keeping the existing recovery-timer math untouched. Reward: replanting **5 plots** during the window earns the **"Christmas 2026"** profile badge. This is the cleanest fit in the whole hub: Canopy's actual mechanic (replant a plot, watch it recover) *is* tree-planting, so the event needs zero new verbs, just a themed skin on an existing button.
2. **Earth Day "Reforestation Week."** Window: Apr 22 (±2 days). Session-summary framing gets a one-line seasonal callout ("This Earth Day, N players restored more forest than they cleared") and the grid's mature-plot tint gets a slightly deeper green for the week. Reward: ending the session with more standing forest value than cleared-resource income during the window earns an **"Earth Day 2027"** badge — this reuses Canopy's own existing comparison-scoring number (Milestone 5) as the qualifying check, so no new tracking is needed.

---

## C. Grid

1. **Earth Hour "Lights Out" week.** Window: last Saturday of March (±3 days) — Earth Hour is a real, dated annual event, which fits Z23's "matching a real holiday or seasonally-relevant date" requirement precisely. For the week, one round per session gets a flavor overlay ("Earth Hour: demand dips as the city switches off for an hour") with a brief cosmetic dimming of the city-skyline-HUD-style meter (if that Round 3 idea ships) or just the round-event text if not. Reward: finishing that flavored round with the grid above 50% clean share earns a **"Earth Hour 2027"** badge. Ties to Grid's actual hope-angle (clean share, not sacrifice) rather than being a generic dark-mode reskin.
2. **COP week "Climate Summit."** Window: the real UN climate conference's dates that year (typically late Nov, e.g. COP hosted at a specific city — check the actual year's dates when this is scheduled, since COP moves). Policy-lever text flavors as "nations pledge new commitments" and renewable build costs get a one-time cosmetic "pledge discount" ribbon on the button (numeric effect optional/skippable if you want zero balance touch at all — the flavor text alone can carry it). Reward: building a renewable plant during the window earns a **"COP Delegate 2026"** badge.

---

## D. Tide

1. **World Oceans Day "Reef Watch" week.** Window: Jun 8 (±3 days) — World Oceans Day is a real UN-recognized date, a strong fit for an ocean-acidification game. Fishing/industry-output button labels swap to a beach-cleanup-flavored variant ("Coastal Cleanup Day" event text in the delayed-effect ticker log), and the acidity meter gets a small coral-reef icon accent for the week — cosmetic only. Reward: investing in adaptation infrastructure at least once during the window earns an **"Oceans Day 2027"** badge, reusing Tide's existing adaptation-investment action as the qualifying check.

---

## E. Aftermath

1. **International Day for Disaster Risk Reduction week.** Window: Oct 13 (±3 days) — a real UN-designated awareness day, and a near-perfect thematic match since Aftermath's whole premise is resilience-building between disasters. Event-sequence flavor text for the week frames the between-events narration around "community preparedness," and the skill-tree unlock panel gets a one-line seasonal blurb. Reward: unlocking any skill-tree node during the window earns a **"Disaster Risk Reduction 2026"** badge — reuses the existing unlock action, no new tracking.

---

## F. Herd

1. **World Environment Day "Methane Watch" week.** Window: Jun 5 (±3 days) — World Environment Day is real and UN-designated, broad enough to comfortably cover agriculture/methane without forcing a narrower, less-real "holiday." Round-event flavor text frames the week's market/regulatory pressure narration around environmental awareness, and the methane meter gets a small leaf-accent border for the week. Reward: investing in any decoupling measure (feed additive, herd cap, capture system) during the window earns an **"Environment Day 2027"** badge, reusing Herd's existing decoupling-investment action.

---

## G. Thaw

1. **International Polar Bear Day week.** Window: Feb 27 (±3 days) — a real, dated, Arctic-specific awareness day, a much better fit for a permafrost game than a generic "winter" reskin would be. The background-trajectory ticker gets a one-line seasonal flavor note, and the permafrost-melt visual gets a small polar-bear-silhouette accent on the region map for the week — purely cosmetic, doesn't touch the feedback-loop math (important given Thaw's own design note that the hope-angle lever here is load-bearing, not decorative). Reward: investing in a permafrost-preserving measure during the window earns a **"Polar Bear Day 2027"** badge.

---

## H. Loop

1. **Global Recycling Day "Closed Loop" week.** Window: Mar 18 (±3 days) — a real, dated recycling-awareness day, a direct fit for a circular-economy game. The circularity-investment buttons (repair/reuse/recycling) get a one-line seasonal callout, and the loop-closure visualization gets a small seasonal ribbon/highlight when it improves during the week. Reward: raising circular-vs-new-extraction percentage at least once during the window earns a **"Recycling Day 2027"** badge — reuses Loop's own existing percentage-tracking system (Milestone 4) as the check, nothing new to build.

---

## I. Drift

1. **World Refugee Day "Welcome Week."** Window: Jun 20 (±3 days) — a real UN-designated date, and thematically the strongest possible fit given Drift's premise is specifically about a receiving region's response to displacement. Integration-service investment flavor text swaps to welcome-week framing, and a well-integrated population milestone gets a small seasonal accent. Reward: investing in integration services during the window earns a **"Refugee Day 2027"** badge, reusing Drift's existing integration-investment action.

---

## L. Le Champ de Mots

1. **Bastille Day "Quatorze Juillet" week.** Window: Jul 14 (±3 days) — Bastille Day is the obvious real-world-date tie for a French-learning game, and it's a genuine cultural touchpoint rather than a forced fit. The farm's cultural-notes toggle (already built) gets extra Bastille-Day-specific cultural content for the week, and completed review sessions during the window get a small French-flag-tricolor accent on the plot border — cosmetic only, no change to grading/SRS logic. Reward: completing a review session during the window earns a **"Quatorze Juillet 2027"** badge.

---

## Shared mechanism — design sketch

Not built. This is a starting shape for whoever picks this up once you've chosen which events (if any) above to actually build, not a spec to implement as-is.

**Core idea:** an event is just a date-gated achievement. The achievements framework already gives every opted-in game an `achievements.json` manifest and an `achievements_earned` field riding the existing save/account system with zero backend changes (`CLAUDE.md` Site-level milestone 8) — a seasonal event badge can piggyback on that exact same plumbing instead of needing anything new. The only genuinely new piece is a small, shared "is an event currently active, and what does it change" check that a game consults at load/tick time.

A game that opts in declares a small `EVENTS` list — plausibly a plain Python list literal in `game.py`, next to wherever `achievements.json` is referenced, something roughly shaped like:

```python
EVENTS = [
    {
        "id": "canopy-christmas-2026",
        "start": "2026-12-20", "end": "2026-12-27",   # real-world dates, checked against local date
        "flavor": {"request_intro": "A family wants a tree for the town square this Christmas..."},
        "badge_id": "christmas-2026",                  # an entry in this game's achievements.json
        "qualifies": lambda state: state["replants_this_event"] >= 5,
    },
]
```

A tiny shared helper (e.g. `shared/seasonal-events.js`, dropped in unchanged the same way `shared/save-widget.js` is today) would do three things: (1) check today's date against each declared event's window and return the active one, if any; (2) if active, let the game swap in the `flavor` overrides and show a small banner/badge indicator, purely presentational; (3) when the event's own `qualifies` check passes, call the existing achievement-grant path to add `badge_id` to `achievements_earned` — the same call path an ordinary achievement already uses, so no new backend endpoint, no new save-schema field, and no new account-side storage beyond what achievements already have.

This keeps the whole feature genuinely optional per game (a game with no `EVENTS` list just never calls the helper), keeps every event cosmetic/reward-only rather than a balance change, and means a future "add event X to game Y" task is scoped as small as writing one dict entry plus one `achievements.json` badge — not a new system per game.

---

## Your answers

Pick which of the above (if any) you want turned into real `planning/TODO.md` checklist items, using the same label style as the other ideas docs (e.g. "B1: yes", "C1: no", "A1: later"). A blank or missing answer is treated as "not yet decided" — nothing here gets built without an explicit yes.

## A


## B


## C


## D


## E


## F


## G


## H


## I


## L


## Shared mechanism

