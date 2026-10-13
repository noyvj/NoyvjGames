"""Start a new game folder from its plan, so the local AI can build its milestones (the QI new-game items).

    python3 scripts/new_game.py <slug> "<Name>"            the folder for milestone 1 (engine and solver)
    python3 scripts/new_game.py <slug> "<Name>" --page     also a minimal working page for milestone 2 (the UI)

Reads planning/<slug>-plan.md. Never overwrites a file that already exists, so it is safe to run again
(for example with --page once milestone 1 is done). Follows the shape of the newest games: after
milestone 1 a game is engine modules plus tests, CLAUDE.md and BUILD-STATUS.md (Zero-G Shift); the page,
game.py and app.js come with milestone 2. Hub registration is separate (scripts/register_game.py).

Base files:  CLAUDE.md (pitch and milestone table from the plan), BUILD-STATUS.md, tests/__init__.py,
             tests/conftest.py (puts the game folder and tools/ on sys.path), tools/ (empty).
--page adds: index.html (shell, then scripts/wire-shared-includes.py adds the site-wide includes),
             style.css, app.js (boots Pyodide, loads ENGINE_MODULES, runs game.py, shows the view),
             game.py (handle / get_state / load_state, the save contract), changelog.json,
             achievements.json, tests/test_shell.py (the contract holds before any feature exists).
"""
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable


def plan_parts(plan_text):
    """The pitch (first paragraph after a 'pitch' heading, else the first paragraph) and milestone rows."""
    pitch = ""
    m = re.search(r"#+[^\n]*pitch[^\n]*\n+(.+?)(?:\n\n|\n#)", plan_text, re.I | re.S)
    if m:
        pitch = " ".join(m.group(1).split())
    if not pitch:
        paras = [p for p in plan_text.split("\n\n") if p.strip() and not p.lstrip().startswith(("#", "|", "-"))]
        pitch = " ".join(paras[0].split()) if paras else ""
    rows = []
    for line in plan_text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if line.lstrip().startswith("|") and len(cells) >= 2 and re.fullmatch(r"M?\d+", cells[0]):
            num = cells[0].lstrip("M")
            name = cells[1]
            content = cells[2] if len(cells) > 2 else ""
            rows.append((num, name, content))
    if not rows:                                     # "Milestone 1: Name" style headings
        for m in re.finditer(r"(?im)^#+\s*(?:milestone|M)\s*(\d+)\s*[:.-]\s*(.+)$", plan_text):
            rows.append((m.group(1), m.group(2).strip(), ""))
    return pitch, rows


def put(path, text, made):
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    made.append(path.relative_to(ROOT).as_posix())


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    slug, name, page = argv[0], argv[1], "--page" in argv
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", slug):
        raise SystemExit("the slug is lowercase words joined by dashes, like zero-g-shift")
    plan = ROOT / "planning" / f"{slug}-plan.md"
    if not plan.exists():
        raise SystemExit(f"no plan at planning/{slug}-plan.md: the game's design comes from there")
    pitch, rows = plan_parts(plan.read_text(encoding="utf-8"))
    gdir = ROOT / "games" / slug
    made = []

    table = "\n".join(f"| {n} | {nm} | {c} | Not started |" for n, nm, c in rows) or "| 1 | (from the plan) | | Not started |"
    put(gdir / "CLAUDE.md", f"""# {name}

Seed: `planning/{slug}-plan.md`. Personal project, no BCM tag, working title. Started {date.today().isoformat()} with `scripts/new_game.py`.
Read the plan first: it holds the design every milestone follows. Then `BUILD-STATUS.md` here.

## One-line pitch
{pitch or "(see the plan)"}

## Stack
- Pyodide Python, plain HTML/CSS, no build step. Engine modules are plain Python with no DOM (the Signal / Lexis
  pattern): `game.py` is the entry point (`handle(json) -> json`, plus `get_state()` / `load_state()` for the
  shared save widget); `app.js` is glue only.
- No audio files. Nothing timed, nothing lost, no luck needed for 100% (the site's standing rules).

## Milestones
| # | Milestone | Content | Status |
|---|-----------|---------|--------|
{table}

## Working conventions
- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag {slug}-milestone-0N`.
- Update the Status column as work happens, and `BUILD-STATUS.md` after every milestone.
- Hub registration is a separate step (`games/{slug}/register.json`, then `scripts/register_game.py {slug}`).
""", made)
    put(gdir / "BUILD-STATUS.md", f"""# {name} build status (handoff file)

Updated after every milestone. Read `planning/{slug}-plan.md`, `CLAUDE.md` here, then this file. Hub registration is NOT part of this build.

## Done
- Folder started with `scripts/new_game.py`.

## Next
- {("M" + rows[0][0] + " " + rows[0][1]) if rows else "Milestone 1 from the plan"}.

## Open problems / notes
- (none yet)
""", made)
    put(gdir / "tests" / "__init__.py", "", made)
    put(gdir / "tests" / "conftest.py", f'''"""{name}'s engine modules are plain Python with no DOM, so the tests import them directly."""

import sys
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
for path in (GAME_DIR, GAME_DIR / "tools"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
''', made)
    put(gdir / "tools" / ".gitkeep", "", made)

    if page:
        put(gdir / "game.py", f'''"""{name} -- the engine entry point. handle(json) -> json is the only thing the page calls; get_state()
and load_state() are the shared save widget's contract (planning/SAVE-BUTTON-INTEGRATION.md): a save is a
plain JSON dict, old saves always load, and a new key appears only when its value is not the default."""

import json

STATE = {{"started": False}}


def _view():
    return {{"title": "{name}", "started": STATE["started"]}}


def handle(request_json):
    try:
        req = json.loads(request_json) if isinstance(request_json, str) else dict(request_json)
    except (TypeError, ValueError):
        req = {{}}
    action = req.get("action")
    if action == "reset":
        STATE.clear()
        STATE.update({{"started": False}})
    elif action == "start":
        STATE["started"] = True
    return json.dumps({{"view": _view()}})


def get_state():
    out = {{}}
    if STATE["started"]:
        out["started"] = True
    return out


def load_state(data):
    if not isinstance(data, dict):
        return False
    STATE["started"] = data.get("started") is True
    return True
''', made)
        put(gdir / "app.js", f'''/* {name}: glue only. Boots Pyodide, writes the engine modules into its file system, runs game.py and
 * shows the engine's view. Every rule lives in Python (game.py and the modules it imports). */
(function () {{
  "use strict";
  var ENGINE_MODULES = [];   // the game's .py modules besides game.py, added milestone by milestone
  var engine = null;
  var STORE_KEY = "{slug}-state";

  function $(id) {{ return document.getElementById(id); }}
  function lsGet(k) {{ try {{ return localStorage.getItem(k); }} catch (e) {{ return null; }} }}
  function lsSet(k, v) {{ try {{ localStorage.setItem(k, v); }} catch (e) {{ /* private mode: play still works */ }} }}

  function send(request) {{
    var view = JSON.parse(engine.handle(JSON.stringify(request))).view;
    render(view);
    lsSet(STORE_KEY, JSON.stringify(engine.getState().toJs({{ dict_converter: Object.fromEntries }})));
    return view;
  }}

  function render(view) {{
    $("view").textContent = view.started ? "Started." : "Press Start.";
  }}

  async function boot() {{
    var pyodide = await window.loadPyodide();
    for (var i = 0; i < ENGINE_MODULES.length; i++) {{
      var source = await (await fetch(ENGINE_MODULES[i], {{ cache: "no-cache" }})).text();
      pyodide.FS.writeFile(ENGINE_MODULES[i], source, {{ encoding: "utf8" }});
    }}
    await pyodide.runPythonAsync(await (await fetch("game.py", {{ cache: "no-cache" }})).text());
    window.pyodide = pyodide;   // the shared save widget looks for it
    engine = {{ handle: pyodide.globals.get("handle"), getState: pyodide.globals.get("get_state"), loadState: pyodide.globals.get("load_state") }};
    var saved = lsGet(STORE_KEY);
    if (saved && saved !== "{{}}") {{
      try {{ engine.loadState(pyodide.toPy(JSON.parse(saved))); }} catch (e) {{ /* a bad save never blocks play */ }}
    }}
    $("engine-status").textContent = "";
    send({{ action: "view" }});
  }}

  document.addEventListener("DOMContentLoaded", function () {{
    $("start-button").addEventListener("click", function () {{ send({{ action: "start" }}); }});
    boot().catch(function (err) {{
      $("engine-status").textContent = "{name} could not start (" + err + "). Reload to try again.";
    }});
  }});
}})();
''', made)
        put(gdir / "index.html", f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{name} - NoyvjGames</title>
<link rel="icon" type="image/svg+xml" href="../../icons/favicon-{slug}.svg">
<link rel="stylesheet" href="style.css">
<script src="../../shared/theme.js"></script>
</head>
<body>
<main id="game">
  <h1>{name}</h1>
  <p id="engine-status" role="status">Starting the engine...</p>
  <div id="view" aria-live="polite"></div>
  <button type="button" id="start-button">Start</button>
</main>
<!-- Pyodide is loaded after first paint, so this shell is readable before the engine is warm. -->
<script src="https://cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide.js"></script>
<script src="app.js"></script>
</body>
</html>
''', made)
        put(gdir / "style.css", f'''/* {name}: the game's own look. The site shell does not style game pages. */
:root {{ color-scheme: dark; --bg: #0e1220; --fg: #e8ecf5; --accent: #7fd1ff; }}
body {{ margin: 0; background: var(--bg); color: var(--fg); font: 16px/1.5 system-ui, sans-serif; }}
#game {{ max-width: 960px; margin: 0 auto; padding: 16px; }}
button {{ font: inherit; min-height: 44px; padding: 0 16px; }}
''', made)
        put(gdir / "changelog.json", json.dumps({"changelog": []}, indent=2) + "\n", made)
        put(gdir / "achievements.json", json.dumps({"game": slug, "achievements": []}, indent=2) + "\n", made)
        put(gdir / "tests" / "test_shell.py", f'''"""The save contract holds before any feature exists: a fresh state saves as an empty dict, survives a
round trip, and junk never breaks loading."""

import json

import game


def setup_function():
    game.handle(json.dumps({{"action": "reset"}}))


def test_a_fresh_game_saves_nothing_so_old_saves_stay_identical():
    assert game.get_state() == {{}}


def test_state_round_trips_through_json():
    game.handle(json.dumps({{"action": "start"}}))
    saved = json.loads(json.dumps(game.get_state()))
    game.handle(json.dumps({{"action": "reset"}}))
    assert game.load_state(saved) is True
    assert game.get_state() == saved


def test_junk_never_breaks_loading():
    for junk in (None, 3, "x", [], {{"started": "yes"}}):
        game.load_state(junk)
    assert json.loads(game.handle("not json"))["view"]["title"] == "{name}"
''', made)
        subprocess.run([PY, str(ROOT / "scripts" / "wire-shared-includes.py")], cwd=ROOT, capture_output=True)

    print(f"games/{slug}: " + (", ".join(made) if made else "nothing new (all files exist)"))
    if page:
        out = subprocess.run([PY, "-m", "pytest", "-q", "-p", "no:cacheprovider"], cwd=gdir, capture_output=True, text=True)
        print("tests: " + (out.stdout.strip().splitlines() or ["(no output)"])[-1])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
