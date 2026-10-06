# Lexis (working title)

Seed: `planning/lexis-plan.md` (decisions section at the top, ladder in 6b). Started 2026-10-06. Not tied to a BCM assessment. NOT hub-linked yet (no `index.html`); registration happens at milestone 5, by the log owner.

## One-line pitch
A sci-fi language-deduction puzzle: a message arrives as bare pulses; learn each language by watching what its signs do, then use it. Deduction first, the story is what pulls you forward.

## Story
You are the communications officer on a survey ship making first contact with new planets; each planet is one language rung (planet 1 is Pulse, a beacon on a quiet world). Original ship, crew, planets and species only: nothing from any existing franchise. The crew voices carry the story between planets and reward each decoded language.

## Stack
Python via Pyodide, engine modules with no DOM (the Signal pattern: a thin view later, `handle(json) -> json` plus `get_state()` / `load_state()` for the save widget). No build step. Glyph art is drawn by code as SVG (project rule: no generated images).

## Core constraints (do not violate without asking)
1. Every word must be DEDUCIBLE from the scenes shown before the player is asked to rely on it. `deduce.py` proves this; `tests/test_deducibility.py` runs it over every curriculum prefix. A new scene or language is not done until its prefixes pass.
2. Scenes are produced by running the real world (`world.react`), never written by hand, so what is watched cannot disagree with what the language means.
3. Guesses are free. The notebook never marks an entry; confirmation says how MANY chosen entries are right, never which.
4. A signal the language cannot say is answered in-world (a stable `reason` code and a line of world text), never an error or a generic "wrong".
5. Everything is deterministic: no random state in play or in the save. Easy to 100%; effects (pulses, shakes) get off switches. No roguelike or deck mechanics.
6. The structure must grow: more languages and districts are new data and rules on the same shapes (`lang.Language`, `Word`), not new code paths (Recommended three languages now, Large five later).

## Modules
- `lang.py`: `Word`, `Language`, number rules (the true one and the wrong ones the checker rules out).
- `pulse.py`: rung 1, the Pulse language (four-mark tokens; class mark then value; words lamp, door, open, shut, end) and the helpers that spell sentences.
- `parse.py`: marks to `Sentence`, or `SignalError(reason, text)`.
- `world.py`: the station (seven lamps and a door), `react(marks, station, language) -> Reaction`.
- `scenes.py`: the ordered Pulse curriculum, generated from the real world.
- `deduce.py`: every reading of the language (3 number rules x 5^5 word meanings), which still fit the scenes, and whether they all behave the same on every sentence the language can form.
- `notebook.py`: `Notebook` and `LexisState` (the save: notebook, scenes seen, what the player has said).

## Milestones
| # | Milestone | Status |
|---|---|---|
| 1 | Engine core: language definition format, the Pulse language, parser, world, scenes, deducibility checker, notebook and save state; 40 tests | **DONE** (2026-10-06, untagged) |
| 2 | Notebook UI, sentence builder, first scene and dialogue playable (static shell + Pyodide engine, `handle(json)`) | not started |
| 3 | Deducibility checker extended to the compound-glyph language; fix any ambiguous word it finds | not started |
| 4 | Rung 2: compound glyphs (every part of a sign means something), glyph stroke grammar to SVG | not started |
| 5 | Save widget, achievements, tutorial, opening screen, hub registration | not started |
| 6 | Rung 3: the bridge language (plural, negation, question markers; borrows from rungs 1 and 2) | not started |
| 7 | Story spine and ending; Info page with real-linguistics sources read live | not started |
| 8 | Polish, accessibility pass (non-colour cues, keyboard, reduced motion), Desktop boot | not started |

## Working conventions
Commit and tag per milestone: `git commit -m "Milestone N: <name>"`, `git tag lexis-milestone-0N`. Update the Status column as work happens.
