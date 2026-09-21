# Undersleep — Groundwork Plan (round-2 M4)

Status: PLAN ONLY. No `games/undersleep/` folder exists yet. Becomes the seed for `games/undersleep/CLAUDE.md`.
User answer (round 2, M4): "yes, i like this idea. there is a lot that can be done to make this more and better and it could also be made somewhat like a life tracker too."
Taste rule: fun first, not teaching. The original pitch's "teaches the cost of sleep debt" framing is dropped; the mechanic just punishes ignoring rhythm, and the game is funny about it. **No medical claims anywhere.**

## One-line pitch
Run one slightly overcommitted person's day: slot work, food, friends and naps into a schedule while their body clock quietly judges you, and optionally let the game mirror your own real sleep and mood.

## Concept
You manage a small character (name, chronotype, a few quirks) across repeating days. Each day you drag **schedule blocks** onto a 24-hour ring. A hidden-then-revealed **circadian curve** decides how good each hour is for each activity: focus work at a low-alertness hour pays little; the same block at the peak pays a lot. Consistency is rewarded: the curve *entrains* (shifts toward) whatever times you keep repeating, and jet-lag-style chaos is punished by drift, not by a lecture. Money/points come from productive blocks; the game is about squeezing value out of a finite body.

Two layers, deliberately separable:
- **Layer A — The Game.** Fully self-contained sim. Playable forever without ever typing a real fact about yourself.
- **Layer B — The Journal (optional life tracker).** A 10-second daily check-in for *your* sleep, mood and energy. The game can reflect it (cosmetically and via one opt-in modifier) but never depends on it.

## Stack
- Default Pyodide Python (root convention): sim logic in `game.py`, plain HTML/CSS, no build step, run via `python -m http.server`.
- Tracker layer is a separate Python module (`journal.py`) and separate JS-side storage adapter, so the sim never imports it (see Separability).
- Ring/curve drawn with inline SVG (no libraries).

## Core constraints
1. No medical, diagnostic or advice language. Fixed footer in tracker: "Undersleep is a game and a personal journal, not a medical tool."
2. No real-time clock dependence for the sim: a "day" advances when the player presses **Run Day** (matches the site's no-timers loader note). The tracker uses the calendar date only to label entries.
3. Tracker data is **local-only by default**; sync is explicit opt-in.
4. Game state and journal state are stored in separate top-level keys and can be deleted independently.
5. Never color-only encoding: meters use icon + number + fill pattern; the curve has labelled peak/trough markers.
6. No shaming copy. Bad days are comedy ("You have achieved horizontal parking").
7. The sim never asks for or penalises real-data honesty; logging nothing is a fully supported way to play.

## Layer A: game design

### Core loop
1. **Plan** the day: place blocks on the 24-hour ring (15-minute snap; keyboard-placeable). Shown: the circadian curve as a translucent wave behind the ring, plus per-block "fit" preview.
2. **Run Day**: the sim steps hour by hour, applying block effects; random **events** interject and ask 1 quick choice.
3. **Debrief**: a receipt of what happened (funny), meter deltas, currency earned, streak of "rhythm days".
4. Spend on unlocks; next day.

### Meters (0-100)
- **Energy** — spent by work/exercise, restored by sleep/rest/food. Sleep debt is a hidden accumulator that lowers next day's *energy ceiling*.
- **Mood** — social, fun, nature, sunlight raise it; overwork, isolation, chaos lower it.
- **Focus** — modifies work/study output; highest at circadian peak, decays with hours awake and with interruption events.
- **Rhythm** (the star meter) — a 0-100 consistency score: how closely today's sleep/wake/meal times match the trailing 5-day average. High Rhythm slowly *narrows and heightens* the peak of the curve (a bonus multiplier up to x1.5); low Rhythm flattens and wobbles it.

### Circadian model (pure function, testable)
`alertness(hour, phase_shift, amplitude)` = base sinusoid + small post-lunch dip harmonic. `phase_shift` moves toward the mean of recent wake times by at most 30 min/day (entrainment). Chronotype sets the starting phase: Lark / Owl / Neither. Amplitude comes from Rhythm. Nothing here claims to be physiologically accurate; it is a game curve.

### Schedule blocks
Work, Deep Work, Meeting (Focus-hungry, needs fixed slot), Sleep, Nap (20/90 min), Meal, Exercise, Friends, Hobby, Errands, Commute, Doomscroll (tempting, restores Mood a bit, steals Energy; mildly funny), Sunlight walk. Blocks have duration, energy cost, mood delta, focus requirement, and a **best-hours tag** that the curve preview highlights.

### Events (~40 at launch, weighted by day/state)
Noisy neighbour, coffee spill, surprise deadline, friend cancels, great idea at 2 a.m., power cut, dog wants out, timezone-hopping colleague, unexpected sunshine. Each: text + 2 choices with trade-offs; a few are chained (a Tuesday problem returns on Friday). Humour in the text; a "personality" narrator ("The Body Clock") comments in short deadpan lines.

### Progression / unlocks
- Currency: **Output** (from productive blocks) and **Goodwill** (from social/mood).
- Unlock new block types, a second character slot, home upgrades (blackout curtains, sunrise lamp, better mattress: flavour + small numeric edges), workplaces with harder schedules (fixed 9-5, night shifts, on-call), and **seasons** (short winter days shift the curve, a mini-challenge).
- **Meta-progression (per-game natural, not a site-wide module)**: "Habits" that persist across characters (e.g. Early Bird trait pool); retiring a character after 30 days grants a "Legacy" point.
- Modes: Story (light arc, toggleable per user's Z11 answer), Sandbox (no fail), Challenge (shift-work week, jet-lag trip).
- No hard fail; low meters produce "Rough Day" penalties (halved output) not game over.

## Layer B: the Journal (optional life tracker)

### What it is
A separate tab. Daily check-in in 3-4 taps:
- **Sleep**: bedtime + wake time (two time pickers, or "same as yesterday" one tap) and a 1-5 quality face row.
- **Mood** 1-5 (icons + words), **Energy** 1-5.
- Optional: one-line note, 1-3 tags (stress, exercise, caffeine, screen-late), 0-2 free-text tags.

### How the game reflects it (all opt-in, per-toggle)
1. **Mirror mode (default when journal is used, cosmetic only):** the character's chronotype starting phase and portrait mood tint are seeded from your logged averages ("Your character woke up a bit like you did").
2. **Rhythm import (opt-in):** your real 7-day consistency becomes a small capped Rhythm bonus (max +10), so honest logging never dominates gameplay and dishonest logging can't break it.
3. **Callback lines:** narrator quotes your own tags back ("You logged 'screen-late' three times. The Body Clock has notes.") Positive/neutral tone only.
Explicitly **not** done: advice, scores of "how well you sleep," targets, comparison to norms, or anything that says what your data means health-wise.

### Design options (with recommendations)
| Decision | Options | Recommendation |
|---|---|---|
| Entry effort | full form vs 3-tap quick log with optional detail | Quick log, expandable detail |
| Backfill | none / last 7 days / any date | Any date, edited inline; missed days are blank, never "0" or shamed |
| Reflection | charts vs insights text | Simple charts only: 30-day sleep-duration bars, mood/energy line, no interpretation text |
| Game coupling | none / cosmetic / numeric | Cosmetic by default; capped numeric bonus behind an explicit toggle |
| Reminders | push/notifications | None (no permissions, PWA scope, avoids nagging) |
| Storage | server-first vs local-first | Local-first, sync opt-in |

## Privacy and ethics
- **Local by default:** journal lives in `localStorage`/IndexedDB under `undersleep_journal_v1`, never sent anywhere unless the player turns on "Sync my journal".
- **Separate consent:** the save widget's normal game sync does **not** include the journal. A second toggle ("Include my journal in my account save") is off by default, with plain-language text about what is stored (dates, times, 1-5 values, notes) and that it's stored on the hub's server database.
- **Data minimisation:** free-text notes are optional and can be excluded from sync even when the rest syncs; no location, no device data, no health API integrations.
- **Controls:** Export (JSON + CSV download), Delete all journal data (confirm-dialog, irreversible, also removes synced copy when signed in), Delete a single entry, "Pause tracking".
- **Backend implication:** sync reuses the existing save-blob path (no new endpoint) — but flag for the user: journal data in the Neon DB is more sensitive than game saves, so the sync layer should use a distinct blob key and be a decision made explicitly (Open question 2). If we don't want to hold it server-side at all, the export/import file is the sole transfer path.
- **Copy audit:** every string reviewed for medical implication; no words like insomnia, disorder, treat, diagnose. Crisis-adjacent tags are not offered; notes are free text but nothing analyses them.
- No third-party analytics; the existing hub ad bar is not shown inside the Journal tab (recommendation), to avoid ad-targeting adjacency.
- Kids: hub audience unknown; no age gating is possible, so the minimal-data stance above matters.

## Separability
- Two modules, two storage keys, two settings groups. `game.py` exports `get_state()`; `journal.py` exports `get_journal()`. Neither imports the other; a thin `bridge.py` (only loaded if "Mirror mode" is on) reads summary stats from the journal and calls documented setters on the game (`seed_chronotype`, `set_rhythm_bonus`).
- A tests rule: the whole game test suite must pass with the bridge and journal modules **deleted** from the import path.
- First-run asks: "Just play" (journal hidden until enabled in Settings) vs "Play and keep a journal." Default is Just play.

## Data model
```json
{
  "schema": 1,
  "game": {
    "day": 0, "character": {"name": "", "chronotype": "neither", "traits": []},
    "meters": {"energy": 80, "mood": 60, "focus": 50, "rhythm": 40},
    "sleep_debt": 0.0, "phase_shift_min": 0,
    "recent_schedules": [], "currency": {"output": 0, "goodwill": 0},
    "unlocks": [], "legacy": 0, "event_flags": {}, "mode": "story"
  },
  "settings": {"text_scale": 1, "reduce_motion": false, "story_mode": true, "journal_enabled": false, "mirror_mode": false, "rhythm_import": false, "sync_journal": false},
  "achievements_earned": {}
}
```
Journal (separate key, only present if used):
```json
{"schema": 1, "entries": {"2026-10-03": {"bed": "23:30", "wake": "07:10", "sleep_q": 3, "mood": 4, "energy": 3, "tags": ["exercise"], "note": ""}}, "paused": false}
```
Rule: the journal is included in `get_state()` for the save widget **only** when `sync_journal` is true; otherwise it is stripped before the widget sees it.

## Shared infrastructure checklist
| Module / convention | Applies? | Note |
|---|---|---|
| `shared/save-widget.js` | Yes | Game state always; journal only under consent flag (needs a filter hook — verify in `SAVE-BUTTON-INTEGRATION.md`) |
| `shared/hub-auth.js` | Yes | Via widget |
| `shared/confirm-dialog.js` | Yes | Delete journal, retire character, reset |
| `shared/tutorial.js` | Yes | Tour covers ring, curve, Run Day; journal tour separate and skippable |
| `shared/mobile-dock.js` / `mobile-hud.js` | Yes | Meters in the HUD, Run Day in the dock |
| `shared/info-page.css` / `info_page.py` | Yes | Info page includes the not-medical-advice statement |
| `shared/personal-best.css` | Yes | Best rhythm streak |
| `shared/ambient-bg.css` | Yes | Slow sky gradient tied to hour-of-day (static under reduce motion) |
| Per-game files | Yes | `achievements.json`, `settings.js`, `changelog.json`, `icons/favicon-undersleep.svg`, feedback/report button, ad bar (except Journal tab) |
| Hub wiring | Yes | Title card, thumbnail class, manifests, last-updated regen |
| Colorblind rule | Yes | Meters icon + number + pattern; curve labelled |

## Achievements (14)
1. Lights Out — first sleep block.
2. Predictable — 3 consecutive Rhythm-70+ days.
3. Metronome — 10-day Rhythm streak.
4. Night Owl / Early Bird — win a day on an off-type schedule.
5. Power Nap — a 20-minute nap lifts Focus at the post-lunch dip.
6. Doomscroller — schedule Doomscroll 5 days in a row (affectionate).
7. Full Ring — fill all 24 hours with no empty slots.
8. Rough Day Survivor — end a Rough Day above 0 Goodwill.
9. Jet-Lagged — finish the jet-lag challenge.
10. Shift Worker — complete the night-shift week.
11. Home Improvement — buy all home upgrades.
12. Legacy — retire a character.
13. Event Collector — see 25 distinct events.
14. Dear Diary (journal) — first check-in; Week of Entries, and Data Owner (export once). All journal achievements are awarded for using the tool, never for the values logged.
Follows `ACHIEVEMENTS-SYSTEM-DESIGN.md`; journal achievements are counted separately so a Just-play user can still reach 100% of the game set.

## Testing approach
- pytest sim harness (SOL-style): circadian curve properties (periodic, peak location follows phase), entrainment cap, meter clamping, sleep-debt accumulation and recovery, Rhythm calculation on synthetic schedules, event weighting determinism with seeded RNG, save round-trip and migration.
- **Separability tests**: game suite passes with journal/bridge removed; `get_state()` excludes journal unless `sync_journal`; toggling it off removes journal from the next save; delete-all removes both local and outbound payload.
- Privacy tests: export contains only the documented fields; capped Rhythm import can't exceed +10.
- Copy lint test: grep all shipped strings against a banned-word list (diagnose, disorder, treat, cure, insomnia, etc.).
- Live checks via `hub-dev-server`: ring drag and keyboard placement, 360px mobile, reduce motion, offline load.

## Milestones
| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Circadian sim core | Curve function, meters, day step, sleep debt; text-only harness playable in tests | Not started |
| 2 | Schedule ring UI | 24-hour SVG ring, block placement (drag + keyboard), curve overlay, Run Day and debrief | Not started |
| 3 | Rhythm + entrainment | Rhythm meter, phase shift, chronotypes, multiplier feedback and visible curve change | Not started |
| 4 | Events + personality | ~40 events, narrator lines, chained events, rough-day handling | Not started |
| 5 | Progression | Currencies, unlocks, home upgrades, workplaces, seasons, retire/legacy | Not started |
| 6 | Save + settings + standard kit | Save widget, `settings.js`, changelog, tutorial, mobile dock/HUD, info page, confirm dialogs | Not started |
| 7 | Achievements | 14 achievements, panel and toast | Not started |
| 8 | Journal (local only) | Quick-log UI, backfill, charts, export/delete, pause, not-medical notice; zero game coupling yet | Not started |
| 9 | Bridge + opt-in sync | Mirror mode, capped Rhythm import, callback lines, journal sync consent flow, separability tests | Not started |
| 10 | Polish + hub integration | Modes (Story/Sandbox/Challenge), copy lint, colorblind audit, title card, manifests, dev-log, tag | Not started |

Commit + tag each: `git tag undersleep-milestone-0N`. Milestones 1-7 ship a complete game with no tracker; 8-9 are an add-on that can be cut without touching the rest.

## Risks
- **Tracker scope creep** into a real health app. Mitigation: hard caps above (3-tap log, no interpretation), milestones 8-9 fully cuttable.
- **Sensitive data on the server.** Mitigation: local default, separate consent, distinct key, export path, deletion that reaches the server.
- **Perceived medical advice** from the curve or narrator. Mitigation: game-curve disclaimers, copy lint test, no thresholds like "you need 8 hours."
- **Circadian sim feeling opaque.** Mitigation: curve overlay always visible, per-block fit preview, debrief explains the biggest swing in plain, funny words.
- **Schedule-planning fatigue** on repeat days. Mitigation: "Repeat yesterday" and saved templates; Run Week button at unlock.
- **Nagging/guilt** loops for real users. Mitigation: no streak on journal, no reminders, blanks are neutral.

## Open questions for the user
1. Journal cloud sync: allow it at all (via existing save system, separate opt-in), or keep the journal strictly local plus manual export/import?
2. If sync is allowed, are you comfortable with that data in the Neon database given it is more personal than game saves? (Would you want it encrypted client-side with a passphrase?)
3. Should the game start with the tracker hidden ("Just play" default, recommended) or present at first run?
4. Tone: deadpan-absurd (recommended) or warmer/cozy?
5. Character: one persistent character, or a roster with "retire and inherit"?
6. Is a hard "Not medical advice" gate at first Journal open (one-time acknowledge) acceptable, or too heavy?
7. Any real-life tags you specifically want (caffeine, exercise, screen-late...) or leave to my defaults?
8. Story mode: a light arc (new job, new city) or sandbox only at launch?
