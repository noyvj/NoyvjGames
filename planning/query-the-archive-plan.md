# Query the Archive (slug `query-the-archive`, TODO QI-35) - Groundwork Plan

Source: the Quick ideas round (G2), owner-approved: "learn simple database queries by finding records in a space-station archive, no deletion allowed." Checked against `PLAYER-PROFILE.md`: coding and logic puzzles (yes), space stations and computers, a notebook that fills in, helper role, short wins, hint ladder, "more game than teaching", no timers, nothing lost. Personal project, no BCM tag, working title. One-line pitch: you are the new records clerk of Cinder Station; every request is a question for the Archive, and the answer is a query you write.

## 1. Concept
The Archive is a database of the station's crew, logs, parts, shipments, repairs and visitors. A **Request slip** arrives in plain words ("Who is on the night shift?", "How many spare valves are in Bay 3?", "Which repair took longest?"). You write a query in a small editor (with clause chips for beginners: tap `SELECT`, `FROM`, `WHERE` to place a ready skeleton), press **Search**, and see a result table. If it matches the request's expected table, the slip is stamped and filed.
- 2-minute session: one slip, `SELECT name FROM crew WHERE deck = 3`, a neat table.
- 20-minute session: a chapter of six slips that builds to a grouped count across two tables.
- Look: dark, calm low-poly "archive stacks" frame with a clean monospace editor and a typeset result table (columns labelled, no colour-only meaning). Quiet; optional generated clicks only.
- **No deletion, ever.** The in-fiction rule is "the Archive does not forget". Technically the database is opened read-only, a SQLite authorizer allows only `SELECT` and the read functions, `PRAGMA`, `ATTACH`, `INSERT`, `UPDATE`, `DELETE`, `DROP` and friends are refused with a kind message, and the database is rebuilt from fixed data every load, so nothing the player does can change it.

## 2. Rules (a pure function of the data, the slip and the query)
- The engine uses Python's built-in `sqlite3` in Pyodide with an in-memory database built from seeded fixed data. A query passes a slip when its result matches the expected result: same columns (by name or position as the slip says), same rows, and same order only when the slip says "in order".
- **Twin check:** every slip is also run against a hidden **twin archive** (same tables, different rows) so hard-coded answers (`WHERE id = 7`) fail while a real query passes both. The player sees the result on the real archive only; the twin appears as "also checked on the backup archive".
- A step budget stops runaway queries (cross joins with huge output) with a friendly note; output is capped.
- Syntax errors are shown in plain words first ("I did not understand near `FORM`. Did you mean `FROM`?") with the raw SQLite message on request.
- No clock, no randomness, no network.

## 3. Content size
- 36 slips in six chapters of six: Looking (`SELECT`, `FROM`), Filtering (`WHERE`, `AND`, `OR`, `LIKE`), Ordering (`ORDER BY`, `LIMIT`, `DISTINCT`), Counting (`COUNT`, `SUM`, `AVG`, `MIN`, `MAX`), Grouping (`GROUP BY`, `HAVING`), Joining (`JOIN`, simple subqueries, `NULL`).
- 7 tables, about 260 rows in the visible archive and a different 260 in the twin; 36 one-line **Archive notes**; a **Clause Drawer** of 20 query keywords that you collect by using them.

## 4. How fairness is PROVED (tests)
- Each slip stores a reference query; tests assert it returns the expected table on both archives and that the slip text has a unique correct table (no other reasonable reading).
- **Near-miss tests:** each slip lists 3 to 6 plausible wrong queries (a missing `DISTINCT`, `>` for `>=`, wrong join) and each must **fail**, so the checker is not too lenient.
- **Safety suite:** a battery of forbidden statements (writes, schema changes, `ATTACH`, `PRAGMA`, `load_extension`, multiple statements, comments tricks) is refused, and a hash of the archive before and after confirms nothing changed.
- Data lint: no real personal data; fixture names are invented. Determinism: archive rebuild is a pure function of a seed constant.

## 5. Bigger picture, goals, hints
- The **Archive Stacks** are the picture: six shelves (chapters) of six drawers (slips) that go from closed to open and filed. A completion percentage bar sits above; the Clause Drawer fills.
- Three goals always visible (any order): the next three unearned achievements with counts and bars. Stats strip: Slips filed, Clauses known, Searches, Tables met.
- Hint ladder (opt-in; first rung asks "Would you like a suggestion?"): Nudge (which table to look at), Hint (the clause to use), Answer (the query shown, with a Use it button; filing it still counts).
- Every chapter and slip is open from the start; the order is a suggestion.

## 6. Achievements (14; computed from facts)
1 First Slip (file 1); 2 Ten Slips; 3 Shelf Done (a whole chapter); 4 Full Archive (all 36); 5 Clean Search (right on the first Search, 10 times); 6 Exact Words (10 slips with no hint); 7 Drawer Half (10 clauses); 8 Drawer Full (all 20); 9 Counted (all aggregates used); 10 Grouped; 11 Joined; 12 Tried and Refused (the Archive turns down a write, once, gently); 13 Tidy Query (match the stored shortest length 5 times); 14 Second Opinion (all three hint rungs on one slip).

## 7. Real-world facts
Fiction: Cinder Station and its people are invented. The About and Sources page cites the SQLite documentation (sqlite.org) and a named history-of-SQL source, read live and dated, as background. More game than teaching.

## 8. Stack, save and reuse
- Pyodide Python with `sqlite3`, plain HTML/CSS, no build step. Modules: `archive.py` (schema, seeded data, twin), `guard.py` (authorizer, forbidden statements, step budget), `slips_*.py`, `check.py`, `drawer.py`, `progress.py`, `hints.py`, `render.py` (table, stacks), `achievements.py`, `info.py`, `game.py`, `app.js`.
- Reuses Repair the Ship's Code's locked-runner idea (a separate module with its own tests), `shared/hint-ladder.js`, `goals-panel.js`, `save-widget.js`, `level-select.js`.
- Save: filed slips with their query text (capped), clauses used, hint rungs, flags. Saved queries run only when the player presses Search, never on load.

## 9. Milestones
| # | Milestone | Content |
|---|-----------|---------|
| 1 | Engine | Seeded archive and twin, read-only guard, checker, chapter 1 (6 slips) with near-miss and safety proofs |
| 2 | Clerk UI | Editor, clause chips, result table, slip stamp, save contract. Playable slice |
| 3 | Chapters 2-4, drawer, hints | 18 more slips, Clause Drawer, hint ladder, three-goals strip |
| 4 | Chapters 5-6 | 12 more slips (36 in all), grouping and joins. First complete game |
| 5 | Standard kit | Opening screen, tutorial, settings, About with live-read sources, What's New, keyboard help, light theme, accessibility pass |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog |

## 10. Open questions for the owner (defaults used meanwhile)
1. Should a "free query" practice desk (no slip, just explore the Archive) be added after the last slip? Default: yes, a read-only sandbox that still counts clauses used toward the Drawer.
2. Clause chips for beginners can be switched off for a typed-only game. Default: chips on until chapter 3, then optional.
