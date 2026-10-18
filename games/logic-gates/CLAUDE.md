# Logic Gates (working title)

Personal project, no BCM tag. Plan: `planning/logic-gates-plan.md` (QI-1 in `planning/TODO.md`). Section code LG.

## One-line pitch
A dead station computer, rebuilt one circuit at a time: wire gates to match a truth table, keep each solved circuit as a chip, and end by wiring a four-instruction computer.

## Standing rules
No timers, energy, grinding or lost progress; no roguelike or deck mechanics; no audio; no generated images (the board is SVG drawn by code); no mandatory leaderboard; no all-good hero. A level is a pure function of the wiring: deterministic, no randomness, no clock (a test scans the engine for it). Every action visibly counts (chips placed, wires drawn, switches flipped, levels solved/at par, sandbox truth tables). Three goals always visible. Display settings live in localStorage, never in the save.

## Stack
Python via Pyodide: DOM-free engine modules, `game.py` with `handle(json)`, `get_state()`, `load_state()`, and a thin JS view (`app.js`). Plain HTML/CSS, no build step.

## Engine modules
| File | Job |
|---|---|
| `chips.py` | the seven gates and the three memory cells (SR latch, D latch, flip-flop) |
| `net.py` | text form for circuits and scripted steps (level data and tests) |
| `sim.py` | flatten built chips into primitives; acyclic pass (all truth-table rows at once as bitsets) or cyclic settle with oscillation detection; power-on state is all 0 |
| `levels_a/b/c.py`, `levels.py` | the 40 levels (data), the chip registry (a level's chip IS its reference circuit), open/unlock rules |
| `check.py` | does a circuit meet a level: truth table or scripted sequence |

## Levels
40 in five chapters (Switches and Lamps 8, Combining Gates 9, Memory 7, Adders 7, A Tiny Computer 9). A level opens when the chips its reference uses are unlocked. Par = reference chip count. Sequence levels start from power-on.

## Milestones
| # | Milestone | Status |
|---|---|---|
| 1 | Engine and level data (chips, simulator, checker, 40 levels) | Done |
| 2 | Board UI (SVG board, chip cards, probe, table, picker, save contract) | Done |
| 3 | Chapters 2-3, hint ladder, sandbox | Done |
| 4 | Chapters 4-5 (adders, the tiny computer) | Done |
| 5 | Standard kit (settings, tutorial, About, changelog, accessibility, light theme) | Done |
| 6 | Achievements (14) | Done |
| 7 | Desktop boot | Done |
| 8 | Wrap-up | Done |
| 9 | Hub registration | BLOCKED ON MAIN SESSION (not done here) |

Open questions for the owner (Lg1-Lg5) are at the end of `planning/logic-gates-plan.md`.

## For the local AI (exact names; every one was checked against the code on 2026-10-18)
- **Files**: engine `game.py` (entry point, all actions, `view()`), `state.py` (the validated save, `new_meta`, `clean_meta`, `level_view`), `chips.py` (gate and memory cell definitions), `sim.py`, `check.py` (does a circuit meet a level), `net.py`, `levels.py` + `levels_a/b/c.py` (the 40 levels as data; chip registry `REGISTRY`), `render.py` (the SVG board), `words.py` (plain-words text), `achievements.py`, `info.py`; page `index.html`, `app.js` (the whole page; engine module list `ENGINE_MODULES` at its top), `chip-drawer.js`, `settings.js`, `pc.js`, `pc-config.json`, generated `pc.html`.
- **Entry points** (the only Python the page calls): `handle(json_string) -> json_string`, `get_state()`, `load_state(proxy)` (it then calls `window.logicGatesRefresh()`). In JS use `send({action: ...})` (app.js; it renders and saves). Never read a Python variable from JS by name. The answer is the WHOLE view; a bad request gives `{"error": ...}` (`unknown action` for a name not in `game.ACTIONS`); a refused move only sets `view.note`.
- **Actions** (`game.ACTIONS`, plus `open` and `reset`): `add {type}` (chip ids such as `not and or xor nand nor xnor sr dlatch dff`; only those in `view.palette`) | `remove {id}` | `wire {dest, src}` (dest `"out:X"` or `"<chipId>.<pin>"`; src `"in:A"`, `"const:0"`, `"const:1"`, `"<chipId>.<outPin>"`, or `""` to cut) | `pick {pin}` (`"s:<src>"` or `"d:<dest>"`, the tap-to-wire path) | `cancel` | `undo` | `clear` | `restore` | `start {level}` (a level id such as `"straight-through"`, or `"sandbox"`) | `next` | `flip {name}` (switch name `A`, `B`, ...) | `script {step}` | `manual` | `hint` | `answer` | `difficulty {level}` (`easy normal hard`).
  A new action = a function `_a_<name>(req)` in `game.py` returning an error string, `"NOEVAL"` (change nothing on the board) or `None`, added to `ACTIONS`, plus a test.
- **Top-level keys of the view** (`game.view`): `note svg svg_width armed target stats goals achievements picker shelf board text palette probe can_undo can_restore level table sandbox info difficulty story hints`. `view.stats`: `solved total par chips wires flips found sixteen`. `view.board`: `chips lamps count cap wires`. `view.level`: `id name ins outs cap loops sandbox kind goal chapter chapter_name index par intro log unlock steps record`. `view.probe`: `inputs step settled`. `view.hints` (None in the sandbox): `rung nudge hint answer answer_used max answer_ready`.
- **get_state() keys**: `schema meta achievements_earned` (`achievements_earned` is write-only, recomputed). `meta` (only non-defaults, written by `state.meta_to_dict`): `levels stats found current work backup tiers`. New save fields: only when non-default, validated field by field in `state.clean_meta` (never raises, `load_state` merges keeping the better).
- **Page**: `render()` in app.js draws one view (it has no event; add a call in `render()` or a `renderX()` it calls). Main ids: `#board-panel`, `#board-holder` (the SVG), `#switches` (buttons `#switch-<name>`), `#palette` (buttons `#add-<chipType>`), `#undo-button`, `#clear-button`, `#restore-button`, `#hint-button`, `#answer-button`, `#next-level-button`, `#result-summary`, `#table-holder`, `#level-goal`, `#solved-banner`, `#toast`, `#status-strip` (`#stat-solved #stat-par #stat-chips #stat-wires #stat-flips`), `#goals`; window panels `#picker-panel`, `#shelf-panel`, `#sandbox-panel`, `#achievements-panel`, `#log-panel`, `#changelog-panel`, `#settings-panel`, `#info-page-panel`; `#engine-status` is empty when the engine is ready.
- **New panel / window**: markup + toggle button in `index.html`, `wirePanelToggle(buttonId, panelId)` in app.js `wire()`, drawing in `render()`; for the Desktop boot add `[panelId, toggleButtonId, title]` to `pc-config.json` `windows` (and an icon or menu id if wanted), then run `/usr/bin/python3 scripts/generate-pc-pages.py` (rewrites every game's `pc.html`; only this game's changes). `tests/test_desktop_boot.py` fails if `pc.html` is stale or a toolbar button is neither icon, menu entry nor window toggle. A new Python module goes into `ENGINE_MODULES` at the top of app.js (`tests/test_assets_and_shell.py` compares it with the `.py` files; `sw.js` is NOT edited by the AI).
- **New browser test**: copy `tests/test_example_browser.py` (uses `tests/browser_helpers.py`: `open_game(p, base)`; script errors are in `page.page_errors`).
- **Tests that pin things a task may change**: `test_game_handle.py` (actions, save round trip, whole game finishes), `test_levels.py` (every level's reference solves it, par = reference chip count) and `test_content.py` (hint and story text per level), `test_check.py`, `test_sim_and_net.py`, `test_difficulty.py` (Normal must stay byte-identical), `test_assets_and_shell.py` (module list, ids, no timers in the view), `test_desktop_boot.py`, `test_accessibility.py`, `test_achievements.py`, `test_gn_oct11.py` (tie boxes), `test_sound.py`.
- **Do not**: invent a view key or an action (copy from above); look up an id in JS that `index.html` or a JS builder does not create; use a clock or `random` in the engine (a test scans for it); change a level's reference circuit or par without rerunning the level tests; put display settings in the save (they are localStorage).

## Playing notes
Chips are earned by solving: a level hands out the chip it builds (a level's reference circuit IS the chip). Memory cells (SR latch, D latch, flip-flop) are modelled directly so the whole computer simulates quickly. A flip-flop never fires on the first look at its clock (power-on). The tiny computer: a 4-bit accumulator, a 2-bit program counter and a 4-word ROM; an instruction word W3 W2 W1 W0 is op (00 add, 01 and, 10 or, 11 xor) then a number 0-3; each clock edge runs ACC = ACC op number.

- GN-5 / GN-6 (2026-10-11, your notes): Desktop hid `#level-unlock` (the line holding "Par is N chips" and the board space) with the other level-head pieces; `pc.css` now shows it inline after the goal sentence, so both pages show par (the "at par" counter in the progress strip was already on both). GN-6: the tie boxes are fixed inputs (a wire tied to 1 or to 0 for good); `words.TIE_TIPS` is their tooltip text (an SVG `<title>` inside each `.lg-const` group in `render.py`), `words.TIE_KEY` is the line `index.html` shows in the board's wire key (`#tie-key`), and both tutorials (`app.js`, `pc.js`) have a "Tie 1 and tie 0" step. The About page was not changed (its facts need a sourced reference, and this is a game-rule explanation, not a real-world fact). Tests: `tests/test_gn_oct11.py`.

## Sound (AU-2, 2026-10-11)
- Optional generated sound from `shared/sfx.js` (Web Audio, no files; off by default; Settings mounts `NoyvjSfx.control()` in `#sfx-setting-slot`). Cues are called only from `app.js` `soundFor(request, previous)` after the engine answers, never from the Python engine: `click_high` when the board's wire count goes up, `click_low` when it goes down, `confirm` the first time the truth table matches, and a delayed `bell` when that first solve also earns a chip. Nothing is communicated by sound alone: the table, the banner and the lamps say everything. The Sources page lists "Generated sound (Web Audio)".

## AN-17 (2026-10-11): difficulty choice (Easy / Normal / Hard)
- Owner answer Pq10. One shared start-of-game choice from `shared/difficulty.js` (`window.NoyvjDifficulty`, `shared/difficulty.css`, tests in `shared/tests/test_difficulty_browser.py`): a labelled radio group in `#difficulty-panel` / `#difficulty-slot` (a `<details>` open until a choice is made; in the Desktop boot it is the first block of the side column). Stored per browser and per game in `localStorage["difficulty:{slug}"]` (never in the save); `app.js` reads it at boot and on change and tells the engine with `{action: "difficulty", level}`; the engine keeps it in a module global (`difficulty`, default `"normal"`) that `reset` and `load_state` leave alone. Switching is allowed at any time (no mid-run lock needed in a puzzle game; `NoyvjDifficulty.setGuard` exists for a game that wants one).
- Design rule: difficulty changes only the surrounding pressure (help and medal bars), never the rules, the content or whether a puzzle can be finished. Normal is today's game: a test runs one scripted session with the level never told, told "normal", and after a detour through Hard and Easy, and requires byte-identical views and saves. Nothing is locked by any choice. Achievements and goals are always computed from the Normal records (so they stay reachable on Normal, and are the same whichever level was played).
- Easy: the first hint press opens the nudge and the hint together (rung 2), the answer button needs only those two rungs (Normal: all three) and has no confirm dialog (the button label says it voids par), and par allows one chip over the reference (`state.EASY_PAR_EXTRA`). Hard: no answer step (`answer` refused, the answer words never shown, ladder capped at 2) and fewer free undos (`state.HARD_UNDO_DEPTH` 12, Normal 60); par stays the reference count because that is already the minimum.
- Records: the Normal record (`levels[id]`: solved, fewest chips, par, hints, answer) is always updated exactly as before, whatever the level, so a clear on Easy or Hard never lowers it; Easy and Hard also keep their own `{chips, par}` per level in `meta["tiers"]` (saved as `meta.tiers`, validated field by field, merged keeping the better). Easy shows a Normal par as its own (it is the stricter result); Hard shows only Hard par. Using the answer on any level sets the sticky `answer` flag, so it voids par everywhere, as ever.
- Tests: `tests/test_difficulty.py` (37).
