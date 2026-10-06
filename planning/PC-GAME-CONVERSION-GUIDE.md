# Converting a game to the Desktop boot: the how-to

Read `planning/PC-VERSION-PLAN.md` first (the why). Continuum is the finished model: read `games/continuum/pc-config.json`, `pc.css`, `pc.js`, `CLAUDE.md` ("Desktop boot") and the generated `pc.html`. The shared code is `shared/pc-shell.js` / `pc-shell.css` / `layout-pref.js` and `scripts/generate-pc-pages.py`.

## What a conversion is

A second entry page, `games/<slug>/pc.html`, for wide windows with a mouse. Same `game.py`, same engine modules, same `game_id`, so saves are shared. `index.html` (Classic) stays as it is, apart from two tiny additions. **No game rule, state or save format changes. No changes to `game.py` at all unless the game genuinely needs a forecast/HUD (see "Optional"); if you think you need one, stop and report instead.**

`pc.html` is GENERATED from `index.html` plus `games/<slug>/pc-config.json`. Never edit `pc.html` by hand. Regenerate with `python3 scripts/generate-pc-pages.py` and check with `--check`.

## Files you create or edit (and nothing else)

1. `games/<slug>/pc-config.json` (new). Schema, with Continuum's as the example:
   - `windows`: `[[panelId, toggleButtonId | null, "Title"], ...]`. Panels that open on demand (achievements, changelog, settings, how to play, summaries, info page...). Each becomes a draggable window; the toggle button is the game's own.
   - `toolbar.icons`: `[[buttonId, "emoji"], ...]` the 2 to 4 buttons used during play. They become icon buttons that forward to the original.
   - `toolbar.menu`: `[{"heading": "...", "ids": [buttonId, ...]}, ...]` every OTHER Classic toolbar button. A test fails if any Classic toolbar button is in neither `icons`, `menu` nor a window toggle. Headings: Game, Help, Records, Scene (use what fits).
   - `composites`: `[{"id": "pc-x-panel", "title", "members": [selectors], "group": "menu heading", "label": "emoji Label"}]` several existing sections shown together in one window opened from the Menu (use for long info/graph/history sections that clutter the main view).
   - `adopt`: `[[nodeSelector, destinationSelector]]` moves a node to the start of another.
   - `zones`: `topbar` (back link, h1, the toolbar div(s), any clock), `stagebar` (small controls above the main thing), `stage` (the main thing you look at), `side` (OPTIONAL right column: only if the game needs a decisions column), `hidden` (elements the game still updates by id but the Desktop layout shows another way, e.g. readouts shown as chips). Selectors may match several nodes. Nodes are MOVED, never copied, so ids and listeners survive.
   - `readouts`: `[["#element-id", "emoji", "Label"], ...]` shell-built chips under the top bar that mirror ordinary text lines like "Funds: 300" (the original keeps updating, usually listed in `zones.hidden` or inside a window).
   - `side_label`: accessible name of the side column.
   - `hints`: `[["P", "Pause"], ...]` ONLY hotkeys the game really has (grep `keydown`/`KeyboardShortcuts` in the game); always include `["Esc", "Menu / close window"]`.
   - `notify`: `{"list": "#log-list"}` if the game has a log list whose new entries should pop up as notifications; `null` otherwise.
2. `games/<slug>/pc.css` (new): layout for THIS game only, every rule scoped under `html[data-layout="pc"]` or an id the shell creates (`#pc-body`, `#pc-stage`, `#pc-side`, `#pc-readouts`...). The generic frame (full-window, top bar, readout chips, windows) is already in `shared/pc-shell.css`; you only add the body grid and game-specific tweaks. Check both the dark and light themes.
3. `games/<slug>/pc.js` (new, only if needed): `window.<SLUG>_PC_TUTORIAL_STEPS = [...]` a Desktop version of the tutorial, because Classic's steps point at panels the Desktop layout moves into windows. Selectors must exist on `pc.html` or be shell-built ids (`#pc-readouts`, `#pc-menu-button`, `#pc-stage`, `#pc-side`, `#pc-topbar`).
4. `games/<slug>/index.html` (two additive edits): a `<script src="../../shared/layout-pref.js" data-game-id="<slug>" data-pc-page="pc.html" data-classic-page="index.html"></script>` right after `<meta name="viewport">`; and, if you wrote pc.js, change the tutorial init to `GameTutorial.init(window.<SLUG>_PC_TUTORIAL_STEPS || <EXISTING_STEPS>, {...})`.
5. `games/<slug>/CLAUDE.md`: a short "Desktop boot" section (what moved where, known limits) and a milestone row.
6. `games/<slug>/changelog.json`: one new player-facing entry (the game's own format; if a test caps the entry count, raise the cap sensibly).

Do NOT edit: `shared/*`, `scripts/*`, `sw.js`, `game.py`, other games, root docs/logs, anything in `planning/`. If you need a shared change (a shell feature, a generator option), do not make it: describe it precisely in your report and work around it in `pc.css` if you can. The owner of the shared files adds `games/<slug>/pc.html`, `pc.css`, `pc.js` to `sw.js`'s precache and writes the dev logs.

## Layout principles (what "PC game" means here)

- No page scroll; the top bar, the main thing you look at (stage), and the decisions fill the window. Decisions and controls the player uses every turn stay visible; long explanatory text, graphs, history and settings move into windows (composites) or the Menu.
- Dashboard games (numbers plus decisions): readout chips across the top (`readouts`), the game's own visual or board as the stage, the decision cards in a right column (`side`), info/graph sections in composite windows.
- Board/stage games: the board is the stage and fills the space; controls for the current selection next to it.
- Keep every control reachable by keyboard; focus order top bar, stage, side. Respect the `hidden` attribute (the site-wide `[hidden]{display:none!important}` is in every stylesheet).
- Dark theme must not cut to black against the page; light theme must be readable.

## Verification (do all of it; report what you could not)

1. `python3 scripts/generate-pc-pages.py` then `python3 scripts/generate-pc-pages.py --check`.
2. `cd games/<slug> && python3 -m pytest -q tests` (all existing tests must pass unchanged) and `python3 -m pytest -q shared/tests` from the repo root (the generic Desktop checks include your game automatically).
3. In the browser (the preview server `hub-dev-server` on port 8073; open your OWN tab with `tabs_create`, pass your `tabId` to every browser call, do not touch other tabs, and set the viewport with `resize_window`): load `http://localhost:8073/games/<slug>/pc.html`. After editing files the page can show stale copies, so reload and, if anything looks old, load the file URL with a cache-busting query in a fetch. Check at 1440x900 and 1024x700: the layout fills the window with no page scroll; nothing important is cut off or overlapping; every window opens and closes (Esc, the close button); the Menu opens with Esc and holds every Classic toolbar button; the readout chips show live values; take a turn or two with the real controls; start the tutorial and step through it (every step's target exists); switch to light theme and look again; read the console for errors. Do NOT write to the live backend: do not submit feedback, ratings or saves (the monkey tests earlier polluted production).
4. Reset the viewport (`resize_window` preset desktop) when done and leave localStorage clean (`localStorage.clear()` on localhost:8073 only if you set test values).

## Report (final message)

Files changed; what the layout is; test counts before and after; what you checked live and what you could not; known limits; any shared-file change you need (precise). Do not run git commands: the owner commits.
