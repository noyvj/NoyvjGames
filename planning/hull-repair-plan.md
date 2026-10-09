# Hull Repair (slug `hull-repair`, section HR, TODO QI-2) - Groundwork Plan

Source: the Quick ideas round, owner-approved: "Flow-Free-style routing of power and pipes across a damaged space-station hull. Every solved board repairs one room on a station map, so the puzzles form a bigger picture." Checked against `PLAYER-PROFILE.md`: Flow Free is a favourite, spatial and logic puzzles first, space and science fiction, dark and moody low-poly, collecting and solving, puzzles that form a bigger picture, three goals visible at all times, easy to 100%, no tutorial needed, no timers, no loss of progress, no all-good hero. Personal project, no BCM tag, working title. The shared baseline (save, settings, achievements, changelog, tutorial, confirm dialog, accessibility, Desktop boot) is the same kit as Robot Script, Logic Gates and Pocket Bazaar.

## 1. Concept
A station called Tern (invented) drifts dark after an accident nobody wants to explain. You are the remote repair link: each room is a routing board of ports, and you lay power and pipe lines between matching ports. Lines may not cross or share a cell. Solve a board and that room comes back on the station map; forty rooms in five decks fill in a cutaway of the whole station. Look: a dark, faceted low-poly cutaway drawn as SVG (two-tone cell facets, jagged holes where the hull is gone, lit lines). Every port, bridge, valve and mixer is told apart by shape and letter, never by colour alone.

## 2. The rules (a pure function of board and paths)
- A board is a grid of 5x5 up to 9x9 cells. Cells: open, hole (hull gone, not playable), bridge, valve (arrow), mixer, and ports. Each line has a source port (solid shape) and a sink port (ringed shape), same letter and same shape.
- Draw a line by dragging from a port (or tapping cells with the keyboard). A line moves one cell at a time and cannot enter a hole or another line's port. Dragging into another line cuts it there; dragging back over your own line trims it. Tapping the end of a line removes one segment.
- Bridge: two lines may cross in a bridge cell, one going straight across and one straight up and down. Valve: the line must pass straight through in the arrow's direction (from source to sink). Mixer: two named lines both end there, one from each side (colour mixing: the mixer takes both and shows the mix).
- A board is **patched** when every line joins its ports, and **restored** when, as well, every open cell is covered. Patched lights the room dimly and unlocks the next board; restored lights it fully. Every authored board has exactly one restored layout (a solver proves it in tests), so the restored layout is the puzzle, and patched is the gentle way through.
- Determinism: validation and solving use no randomness and no clock. A saved layout is re-checked on load.

## 3. Boards: 40 in five decks (chapters), 8 boards each
1. **Docking Ring** (5x5 to 6x6): plain lines, 2 to 4 of them.
2. **Crew Deck** (6x6 to 7x7): adds damaged cells (holes) that change the outline of the room.
3. **Engineering** (6x6 to 7x7): adds bridges.
4. **Life Support** (7x7 to 8x8): adds one-way valves, with bridges and holes.
5. **The Core** (8x8 to 9x9): adds mixers and uses everything.
- A deck opens when 5 of the previous deck's 8 boards are patched (never all). Inside a deck, any board in any order.

## 4. The station map and the repair log (free collectable)
- The Station panel is a cutaway: five decks, eight rooms each. A room is dark and cracked, patched (dim, dashed ring) or restored (lit, check mark); states differ by shape and word as well as light. The hull outline brightens with the share restored. Tapping a room opens its board.
- Repair log: every patched room adds its name and a short, quiet log line, kept in a Log panel as a notebook that fills in (40 entries, nothing hidden, nothing missable, no day matters). Voices are tired crew and managers who cut corners; nobody is a hero. Story lines sit behind the shared story toggle; nothing needed to play is in them.

## 5. Easy to 100%, hints, goals
- Hint ladder per board, free, never touching a state: Nudge (one sentence about where to start), Hint (shows the opening cells of one line as a ghost), Answer (the whole layout as a ghost, with a button to lay it). Using the answer is never shamed; it counts as a clear and a restore.
- Every board's restored layout exists, is stored, and is proven unique, so 100% is always reachable. States only go up; nothing expires; nothing is lost by undoing or clearing.
- A strip of the next three goals (any order, with progress such as "Patch 10 rooms 4/10"), always visible. Stats strip: Rooms patched, Rooms restored, Pipe laid, Hints. Tally panel: pipe erased, undos, boards cleared again, hints by rung. Every drag, erase and hint moves one number.

## 6. Achievements (14; computed from facts; none hidden, none luck or time based)
1 First Spark (patch 1); 2 Ten Lit (patch 10); 3 Deck Patched (patch every room of one deck); 4 Three Decks (3 decks); 5 Station Lit (patch all 40); 6 Tidy Work (restore 5); 7 Careful Hands (restore 20); 8 Hull Whole (restore all 40); 9 Over and Under (clear a board with a bridge crossing); 10 Mind the Valve (clear a board with a valve); 11 Colour Theory (clear a board with a mixer); 12 Second Thoughts (clear a board after erasing a line on it); 13 Second Opinion (climb all three hint rungs on one board); 14 Pipe Layer (lay 500 cells of pipe).

## 7. Stack, save and tests
- Pyodide Python, plain HTML/CSS, no build step. Engine: `rules.py` (grid, chains, validation), `play.py` (drawing state and drag steps), `boards_*.py` (40 boards with stored layouts), `logbook.py`, `progress.py`, `hints.py`, `render.py` (board, lines and station map SVG), `achievements.py`, `info.py`, `game.py` (`handle(json)`, `get_state()`, `load_state()`); `app.js` is glue (pointer drag, keyboard, playback of nothing: results are instant). Dev-only `tools/solver.py` (exhaustive, counts layouts) and `tools/gen.py` (finds boards with a seed; its output is frozen into the `boards_*.py` data).
- Save: per board the best layout (compact text, re-validated on load), unfinished drafts, hint rungs, flags, tally. Only fully validated state loads; new keys appear only when non-default; `achievements_earned` is written and never read back.
- Tests: rule semantics per twist, solver on every board (solvable, exactly one restored layout, stored layout equals it), save round trip and tampering, hints, achievements all reachable by a layout-only player, accessibility and shell checks, pledge (no clock, no randomness, no timers).

## 8. Milestones
| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Engine | rules, drawing state, solver, deck 1 (8 boards) with proofs and tests | Done |
| 2 | Board UI | SVG board, pointer and keyboard drawing, result card, board picker, favicon, settings, save contract. Playable slice | Done |
| 3 | Decks 2-3, map, log, hints | 16 more boards, deck gating, station map, repair log, hint ladder, three-goals strip | Done |
| 4 | Decks 4-5 | 16 more boards (40 in all) with valves and mixers. First complete game | Done |
| 5 | Standard kit | Opening screen, tutorial, About, What's New, keyboard help, confirm dialogs, light theme, accessibility pass | Done |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test | Planned |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog | Planned |

## 9. Open questions for the owner (defaults used meanwhile)
1. Restored needs every cell covered, patched needs only the connections. Is that the right split, or should patched be enough for the map? Default: both states, map shows both.
2. Should a deck open at 5 of 8 patched, or should every board be open from the start? Default: 5 of 8.
3. Is the station story (a tired crew, shortcuts, an accident no one explains) the right quiet tone, or should the log be shorter or off by default? Default: short, behind the story toggle.
4. Should there be a free "workbench" mode (draw your own board and have the solver check it) after the last deck? Default: no.
5. Valves and mixers arrive late (decks 4 and 5). Bring one of them into deck 2 instead? Default: as written.
