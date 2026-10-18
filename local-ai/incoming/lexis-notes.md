# Lexis: LA-8 notes (drafted 2026-10-18)

Steps are in `local-ai/incoming/lexis.txt` (a header line only, lint: 0 problems). 10 open items labelled `[local AI: after split]`.

## A list (relabel `[local AI: yes]`)
None.

## B list (chains)
None.

## C list (not for the local AI)
Lexis' first rule is that every word of every language must be deducible from the scenes shown (`deduce.py` / `deduce_compound.py` / `deduce_bridge.py`, pinned by `tests/test_deducibility.py`), and scenes are produced by running the real world, never written by hand. Every item that adds a planet or puzzle mode (a new language) therefore needs a new language, a new world, a new deducibility checker and a curriculum that passes it. That is a design and proof task, not an exact step, and the checkers are the one place a weak model cannot be trusted to know when it is wrong. The story items need authored prose that must not name or explain any sign (`tests/test_story.py`), which is the owner's voice.

| Item | Label | Reason |
|------|-------|--------|
| R4-PX-1 the machine planet | `[Claude: design]` | A language that is a tiny instruction set plus "write a short program": a new language, a machine world, a checker that proves the instruction meanings deducible and a rule for what a valid program is. Growth path "planets 4 and 5" in the plan. |
| R4-PX-2 the broken guardian | `[needs you]` | A quiet, tragic character story told through a log: authored prose in the owner's voice, optional reading, and it must not explain any sign. |
| R4-PX-3 crew choices | `[needs you]` | Short branching talks between planets with a captain who makes real mistakes: authored dialogue and branching rules; nothing in `story.py` branches today. |
| R4-PX-7 branching voyage | `[needs you]` | The owner's own note changes the shape (all planets are reached in the end, each opens with the same message in a different language, order only changes the crew's reactions). That needs the language ladder, the contact goals and `story.py` redesigned so the order is free; planet 2 and 3 currently unlock in sequence. |
| R4-PX-8 the silent courier | `[Claude: design]` | A drone that answers only in signs already learned, with meaning growing as you learn: a new interaction model on top of three languages, plus its animation and tone. |
| R4-PX-13 grammar filter | `[Claude: design]` | Decide which garbled messages obey a language's rules, like regular expressions: a new puzzle with a generator and a solver that must prove each case has one right answer. |
| R4-PX-15 spectrum planet | `[Claude: design]` | A planet speaking in light lines, with the player deciding which element each means: a new language, real spectral data (live web data for accuracy) and drawn art, all without generated images. |
| R4-PX-17 sign tiles | `[Claude: design]` | A Baba-Is-You-style sandbox where sliding signs changes a world rule: a rules engine, a board, levels and a solver. A new game inside the game. |
| R4-PX-18 path panels | `[Claude: design]` | Draw a path through signs that spells a valid message (a Witness-style puzzle): path input over an SVG board, a generator that proves one solution, and the grammar of messages. |
| R4-PX-19 evidence board | `[needs you]` | Looks already built: the Evidence board (Round 4 extras, audited 2026-10-17) lets you pin the received Pulse transmissions and name each one (`name_pin {pin, text}`, `evidence_pins` in the save, `_evidence_view()` in `game.py`, the board in `app-4-boards.js`). Say whether to tick this item as done or what is still missing (for example fragments from planets 2 and 3, or a calmer "something is sending this" framing). |

| Item | Decision | Steps |
|------|----------|-------|
| R4-PX-1 | C | 0 |
| R4-PX-2 | C | 0 |
| R4-PX-3 | C | 0 |
| R4-PX-7 | C | 0 |
| R4-PX-8 | C | 0 |
| R4-PX-13 | C | 0 |
| R4-PX-15 | C | 0 |
| R4-PX-17 | C | 0 |
| R4-PX-18 | C | 0 |
| R4-PX-19 | C | 0 |

Totals: A 0, B 0, C 10.
