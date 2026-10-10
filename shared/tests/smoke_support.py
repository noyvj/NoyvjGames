"""Support code for the 'smoke everything' harness (planning/TODO.md Z-11) and the save-fixture
generator (scripts/generate-save-fixtures.py). Not a test module itself (no `test_` prefix).

How a game is booted without a browser
--------------------------------------
Every older game ships a pytest fixture `game_env` in `games/<slug>/tests/conftest.py` that loads
`game.py` against a fake DOM (`FakeElement`s keyed by id, a fake `js` and `pyodide` module). This
module imports that conftest under a unique package name and calls the fixture's own function, so
the games' boot code is exactly the one their own tests use and nothing is duplicated. The
engine-style games (Signal, Chronicle, Lexis, Heist Committee, Lighthouse, Pocket Bazaar, Dead Reckoning, Logic Gates, Robot Script, Hull Repair, Station Medic, Stranded) have no DOM: their `game.py` is a plain module with
a request/response entry point, driven here with a small action grammar instead of clicks.

Importing a game's tests package changes `sys.path` and `sys.modules` (every game's module is
called `game`); `isolated_imports()` puts both back so the games cannot leak into each other or
into the other shared tests.
"""

import contextlib
import importlib
import importlib.util
import json
import math
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GAMES = ROOT / "games"

# Signed on purpose: a profit/loss line, a delta, a percentage swing. Negative numbers under keys
# like these are information, not a broken resource.
SIGNED_KEY = re.compile(r"(^|_)(net|delta|change|diff|pct|percent|offset|trend|slope|balance_change)(_|$)", re.I)


class Ev:
    """The click event object handed to fake-DOM handlers (the games' own tests pass None; this
    one also answers the few members a handler might read)."""

    def __init__(self, target):
        self.target = target
        self.currentTarget = target
        self.key = "Enter"
        self.shiftKey = False
        self.ctrlKey = False

    def preventDefault(self):
        pass

    def stopPropagation(self):
        pass


# -- import isolation ----------------------------------------------------------------------------

@contextlib.contextmanager
def isolated_imports():
    """Restore sys.path and sys.modules on exit, so whatever a game's conftest imported (or
    inserted into the path) disappears again."""
    saved_path = list(sys.path)
    saved_modules = dict(sys.modules)
    try:
        yield
    finally:
        sys.path[:] = saved_path
        for name in list(sys.modules):
            if name not in saved_modules:
                del sys.modules[name]
        sys.modules.update(saved_modules)      # a game module that shadowed an already-imported name goes away again


def load_conftest(slug):
    """Import games/<slug>/tests as a package with a unique name and return its conftest module."""
    tests_dir = GAMES / slug / "tests"
    name = slug.replace("-", "_") + "_gametests"
    spec = importlib.util.spec_from_file_location(name, tests_dir / "__init__.py",
                                                  submodule_search_locations=[str(tests_dir)])
    package = importlib.util.module_from_spec(spec)
    sys.modules[name] = package
    spec.loader.exec_module(package)
    return importlib.import_module(name + ".conftest")


def fixture_function(fixture):
    """The plain function behind a pytest fixture object (pytest 8 wraps it)."""
    return getattr(fixture, "__wrapped__", None) or fixture._get_wrapped_function()


@contextlib.contextmanager
def fake_dom_game(slug):
    """Yield the game's `GameEnv` (`.module`, `.elements`, `.timers`...) booted on a fresh fake
    DOM, using the game's own `game_env` fixture, and tear it down afterwards."""
    with isolated_imports():
        conftest = load_conftest(slug)
        generator = fixture_function(conftest.game_env)()
        env = next(generator)
        try:
            yield env
        finally:
            generator.close()


# -- state checks --------------------------------------------------------------------------------

def walk_numbers(obj, path=""):
    """Yield (path, key, number) for every numeric leaf of a JSON-like structure (bools skipped)."""
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)):
        yield path, path.rsplit("/", 1)[-1], obj
    elif isinstance(obj, dict):
        for key, value in obj.items():
            yield from walk_numbers(value, "%s/%s" % (path, key))
    elif isinstance(obj, (list, tuple)):
        for i, value in enumerate(obj):
            yield from walk_numbers(value, "%s/%d" % (path, i))


def state_problems(state, signed_ok=(), where=""):
    """Problems in one `get_state()` result: not JSON-clean, NaN or infinity, a negative number
    under a key that is not signed by design. `signed_ok` is an extra regex (string) of paths or
    keys that may be negative for this game."""
    problems = []
    try:
        json.dumps(state, allow_nan=False)
    except (TypeError, ValueError) as exc:
        problems.append("%sstate is not clean JSON: %s" % (where, exc))
    extra = re.compile(signed_ok) if signed_ok else None
    for path, key, value in walk_numbers(state):
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            problems.append("%s%s is %r" % (where, path, value))
        elif value < 0 and not SIGNED_KEY.search(key) and not (extra and extra.search(path)):
            problems.append("%s%s is negative (%r)" % (where, path, value))
    return problems


# -- the fuzzers -----------------------------------------------------------------------------

def live_buttons(env):
    """Sorted ids of elements with a live click handler that are enabled and shown."""
    out = []
    for key, element in env.elements.items():
        if element.disabled or getattr(element, "hidden", False):
            continue
        handlers = element._listeners.get("click", [])
        if any(not getattr(h, "destroyed", False) for h in handlers):
            out.append(key)
    return sorted(out)


def fuzz_fake_dom(env, seed, steps, check_every=5, signed_ok=()):
    """Click a seeded-random enabled button `steps` times. Returns a summary dict with
    `errors` (handler exceptions and bad states, as strings), `clicks` and `distinct`."""
    rng = random.Random(seed)
    random.seed(seed)                       # games that draw from the global RNG stay repeatable
    errors, clicked = [], set()
    clicks = 0
    for step in range(steps):
        candidates = live_buttons(env)
        if not candidates:
            break
        key = rng.choice(candidates)
        element = env.elements[key]
        try:
            element.dispatch("click", Ev(element))
            clicks += 1
            clicked.add(key)
        except Exception as exc:  # noqa: BLE001
            errors.append("step %d clicking #%s raised %s: %s" % (step, key, type(exc).__name__, exc))
            break
        timers = getattr(env, "timers", None)
        if timers is not None and step % 7 == 0:
            try:
                timers.flush()
            except Exception as exc:  # noqa: BLE001
                errors.append("step %d flushing timers raised %s: %s" % (step, type(exc).__name__, exc))
                break
        if step % check_every == 0 or step == steps - 1:
            errors += _check(env.module.get_state, signed_ok, "step %d: " % step)
            if errors:
                break
    if not errors:
        errors += _check(env.module.get_state, signed_ok, "final: ")
    return {"errors": errors, "clicks": clicks, "distinct": len(clicked)}


def _check(get_state, signed_ok, where):
    try:
        state = get_state()
    except Exception as exc:  # noqa: BLE001
        return ["%sget_state() raised %s: %s" % (where, type(exc).__name__, exc)]
    return state_problems(state, signed_ok, where)


# Engine-style games: a request dict in, a response dict out ------------------------------------

def fuzz_requests(call, get_state, next_request, seed, steps, check_every=5, signed_ok=()):
    """`next_request(rng, last_response)` returns a request dict; `call(request)` runs it. A
    response that is not a dict, or an exception, is an error."""
    rng = random.Random(seed)
    random.seed(seed)
    errors, last, calls, kinds = [], None, 0, set()
    for step in range(steps):
        request = next_request(rng, last)
        try:
            last = call(request)
            calls += 1
            kinds.add(request.get("action"))
        except Exception as exc:  # noqa: BLE001
            errors.append("step %d request %r raised %s: %s" % (step, request, type(exc).__name__, exc))
            break
        if not isinstance(last, dict):
            errors.append("step %d request %r returned %s, not a dict" % (step, request, type(last).__name__))
            break
        if step % check_every == 0 or step == steps - 1:
            errors += _check(get_state, signed_ok, "step %d: " % step)
            if errors:
                break
    return {"errors": errors, "clicks": calls, "distinct": len(kinds)}


def signal_request(rng, last):
    r, c = rng.randrange(0, 8), rng.randrange(0, 8)
    roll = rng.random()
    if roll < 0.40:
        return {"action": "ping", "r": r, "c": c}
    if roll < 0.70:
        return {"action": "mark", "r": r, "c": c}
    if roll < 0.76:
        return {"action": "clear_marks"}
    if roll < 0.88:
        return {"action": "commit"}
    if roll < 0.90:
        return {"action": "give_up"}
    if roll < 0.94:
        return {"action": "practice", "mode": rng.choice(["easy", "normal", "hard", None])}
    if roll < 0.97:
        return {"action": "share"}
    return {"action": rng.choice(["view", "stats", "achievements", "boot", "ack_onboarding"])}


def chronicle_request(rng, last):
    view = (last or {}).get("view") or {}
    puzzle = view.get("puzzle") or {}
    tray = puzzle.get("tray") or []
    slots = puzzle.get("slots") or []
    sections = [s["id"] for s in view.get("sections", []) if s.get("unlocked")]
    roll = rng.random()
    if roll < 0.12 and sections:
        return {"action": "start", "section": rng.choice(sections)}
    if roll < 0.55 and tray and slots:
        return {"action": "place", "event": rng.choice(tray), "slot": rng.randrange(len(slots))}
    if roll < 0.65 and slots:
        return {"action": "unplace", "slot": rng.randrange(len(slots))}
    if roll < 0.82:
        return {"action": "check"}
    if roll < 0.88:
        return {"action": "show_answer"}
    if roll < 0.95:
        return {"action": "next"}
    return {"action": rng.choice(["boot", "mode"]), **({"mode": rng.choice(["timeline", "web", "myth", "review"])} if rng.random() < 0.5 else {})}


def lexis_request(rng, last):
    planet = rng.choice(["pulse", "pulse", "compound", "bridge"])
    roll = rng.random()
    bits = lambda n: "".join(rng.choice("01") for _ in range(n))  # noqa: E731
    if roll < 0.30:
        return {"action": "next_scene", "planet": planet}
    if roll < 0.50:
        return {"action": "write", "planet": planet, "form": bits(rng.choice([3, 4, 5])),
                "gloss": rng.choice(["door", "lamp", "yes", "no", ""])}
    if roll < 0.60:
        return {"action": "confirm", "planet": planet, "forms": [bits(rng.choice([3, 4, 5])) for _ in range(rng.randrange(0, 5))]}
    if roll < 0.90:
        return {"action": "speak", "planet": planet, "marks": bits(rng.randrange(0, 8)),
                "glyph": rng.choice(["ku", "tu", "ra", "", "zz"]),
                "message": rng.choice(["ka", "ku tu", "what is this", "", "ka ka ka"])}
    return {"action": rng.choice(["open", "open", "reset"]), "planet": planet}


def heist_request(rng, last):
    """Heist Committee: follow the phase the last response reported (board, scout, recruit, plan,
    playback, payout), mostly with valid moves and now and then with a stray one."""
    view = (last or {}).get("view") or {}
    phase = view.get("phase", "board")
    roll = rng.random()
    if roll < 0.04:
        return {"action": rng.choice(["open", "undo", "redo", "abandon", "clear_plan", "info", "bogus"])}
    if phase == "board":
        ids = [card["id"] for card in view.get("board", [])]
        return {"action": "take_job", "target": rng.choice(ids)} if ids else {"action": "open"}
    if phase == "scout":
        return rng.choice([{"action": "scout", "level": rng.randrange(0, 4)}, {"action": "to_recruit"},
                           {"action": "to_recruit"}, {"action": "back_to_board"}])
    if phase == "recruit":
        offer = [c["id"] for c in view.get("offer", [])]
        gear = [g["id"] for g in view.get("gear", [])]
        picks = [{"action": "confirm_crew"}]
        if offer:
            picks += [{"action": "hire", "crew": rng.choice(offer)}] * 4
            picks += [{"action": "background", "crew": rng.choice(offer)}]
        if gear:
            picks += [{"action": "gear", "gear": rng.choice(gear)}]
        return rng.choice(picks)
    if phase == "plan":
        beats = max(1, int((view.get("target") or {}).get("beats", 6)))
        tray = [a["id"] for a in view.get("tray", [])] or ["wait"]
        lane, beat = rng.randrange(0, 5), rng.randrange(0, beats)
        if roll < 0.60:
            return {"action": "place", "lane": lane, "beat": beat, "cell": rng.choice(tray)}
        if roll < 0.68:
            return {"action": "clear", "lane": lane, "beat": beat}
        if roll < 0.74:
            return {"action": "move_cell", "lane": lane, "beat": beat, "to_lane": rng.randrange(0, 5), "to_beat": rng.randrange(0, beats)}
        if roll < 0.78:
            return {"action": "move_lane", "lane": lane, "to_lane": rng.randrange(0, 5)}
        return {"action": "start_heist"}
    if phase == "playback":
        return rng.choice([{"action": "step"}] * 4 + [{"action": "skip"}, {"action": "finish"}, {"action": "finish"}])
    return rng.choice([{"action": "retry"}, {"action": "back_to_board"}, {"action": "back_to_board"}])


def lighthouse_request(rng, last):
    """Lighthouse: follow the phase the last response reported (evening, night, morning, day, yearend)."""
    phase = ((last or {}).get("phase")) or "evening"
    roll = rng.random()
    parts = ["tower", "lantern", "rail", "dock", "cistern"]
    if roll < 0.04:
        return {"action": rng.choice(["open", "settings", "abandon", "bogus", "read_letter", "reply"]),
                "eerie": rng.random() < 0.5, "id": rng.choice(["a", "b", ""]), "seed": rng.randrange(1, 999)}
    if phase == "evening":
        if roll < 0.35:
            return {"action": "plan", "levels": [rng.choice(["dim", "standard", "bright", "storm"]) for _ in range(3)],
                    "tasks": {"wind": rng.random() < 0.5, "watch": rng.random() < 0.5, "repair": rng.random() < 0.5},
                    "ration": rng.choice([0, 5, 20]), "focus": rng.choice(["worst"] + parts)}
        if roll < 0.45:
            return {"action": "upgrade", "id": rng.choice([u["id"] for u in (last or {}).get("upgrades", [])] or ["x"])}
        return {"action": "start_night"}
    if phase == "night":
        if roll < 0.55:
            return {"action": "step", "n": rng.choice([1, 3, 10, 40])}
        return rng.choice([{"action": "level", "level": rng.choice(["dim", "standard", "bright", "storm"])},
                           {"action": "wind"}, {"action": "tend"}, {"action": "patch", "part": rng.choice(parts)},
                           {"action": "step", "n": 25}])
    if phase == "morning":
        return {"action": "end_morning"}
    if phase == "day":
        if roll < 0.60:
            return {"action": "day", "task": rng.choice(["repair", "rest", "tidy", "beachcomb", "garden", "rescue"]),
                    "part": rng.choice(parts), "id": rng.choice(["a", "b"])}
        if roll < 0.70:
            return {"action": "upgrade", "id": rng.choice([u["id"] for u in (last or {}).get("upgrades", [])] or ["x"])}
        if roll < 0.78:
            return {"action": "order", "order": {k: rng.randrange(0, 5) for k in ["oil", "wick", "timber", "food", "cloth"]}}
        return {"action": "end_day"}
    return {"action": rng.choice(["continue", "continue", "abandon", "end_day"])}


def pocket_request(rng, last):
    """Pocket Bazaar: open a market day, then crate, merge, deliver, sell and sweep on the board it reports."""
    view = last or {}
    board = view.get("board")
    roll = rng.random()
    if roll < 0.03:
        return {"action": rng.choice(["open", "reset", "bogus", "buy", "buy_decor", "put_decor"]), "id": rng.choice(["x", "", "broom"])}
    if not board:
        if roll < 0.30:
            ups = [u.get("id") for u in view.get("upgrades", []) if isinstance(u, dict)]
            return {"action": "buy", "id": rng.choice(ups or ["x"])}
        return {"action": "start_day"}
    cells = board.get("cells") or []
    n = max(1, len(cells))
    families = view.get("unlocked_families") or ["x"]
    if roll < 0.30:
        return {"action": "crate", "family": rng.choice(families)}
    if roll < 0.60:
        return {"action": "drop", "from": rng.randrange(n), "to": rng.randrange(n)}
    if roll < 0.80:
        return {"action": "deliver", "from": rng.randrange(n), "to": rng.randrange(3)}
    if roll < 0.90:
        return {"action": "sell", "at": rng.randrange(n)}
    return {"action": "broom", "at": rng.randrange(n)}


def reckoning_request(rng, last):
    """Dead Reckoning: pick a chart or a practice chart, plan legs, sail, then retry, restart or go on."""
    view = last or {}
    roll = rng.random()
    chart_ids = [c["id"] for ch in view.get("picker", []) if ch.get("unlocked", True) for c in ch.get("charts", [])]
    if roll < 0.05:
        return {"action": rng.choice(["open", "reset", "bogus", "undo", "clear", "restart", "allow", "clear_point", "show_par", "use_par"]),
                "value": rng.random() < 0.5}
    if roll < 0.10:
        return {"action": "start", "chart_id": rng.choice(chart_ids or ["x"])}
    if roll < 0.14:
        return {"action": "practice", "difficulty": rng.choice([1, 2, 3, 4, 5]), "seed": rng.choice([None, rng.randrange(0, 1000)])}
    if view.get("phase") == "reveal":
        return {"action": rng.choice(["retry", "next_chart", "retry", "restart", "show_par"])}
    leg = rng.randrange(0, 4)
    if roll < 0.34:
        return {"action": "add_leg"}
    if roll < 0.46:
        return {"action": "set_leg", "i": leg, "heading": rng.randrange(0, 360), "speed": rng.uniform(0, 9), "hours": rng.uniform(0, 6)}
    if roll < 0.54:
        return {"action": "nudge", "i": leg, "field": rng.choice(["heading", "speed", "hours"]), "delta": rng.choice([-10, -1, 1, 10])}
    if roll < 0.60:
        return {"action": "remove_leg", "i": leg}
    if roll < 0.66:
        return {"action": "helper", "kind": rng.choice(["naive", "current"]), "target": rng.choice(["dest", "point"])}
    if roll < 0.70:
        return {"action": "point", "x": rng.uniform(0, 30), "y": rng.uniform(0, 30)}
    if roll < 0.74:
        return {"action": rng.choice(["take_fix", "add_wait", "set_mode"]), "landmark": rng.choice(["a", "b", "c"]), "mode": rng.choice(["plan", "watch"])}
    return {"action": rng.choice(["sail", "sail", "anchor"])}


def gates_request(rng, last):
    """Logic Gates: open a level, put chips on the board, wire pins to the sources the view offers, flip switches, climb the hints."""
    view = last or {}
    roll = rng.random()
    board = view.get("board") or {}
    if roll < 0.04:
        return {"action": rng.choice(["open", "reset", "bogus", "undo", "clear", "restore", "cancel", "manual", "next"])}
    if roll < 0.10:
        ids = [lv["id"] for ch in view.get("picker", []) for lv in ch.get("levels", []) if lv.get("open")]
        return {"action": "start", "level": rng.choice(ids + ["sandbox"] if ids else ["sandbox"])}
    if roll < 0.28:
        types = [p["type"] for p in view.get("palette", [])] or ["and"]
        return {"action": "add", "type": rng.choice(types)}
    pins = [pin for chip in board.get("chips", []) for pin in chip.get("ins", [])] + list(board.get("lamps", []))
    if roll < 0.62 and pins:
        pin = rng.choice(pins)
        sources = [o["value"] for o in pin.get("options", [])]
        return {"action": "wire", "dest": pin["dest"], "src": rng.choice(sources or [""])}
    if roll < 0.70 and board.get("chips"):
        return {"action": "remove", "id": rng.choice(board["chips"])["id"]}
    if roll < 0.82:
        names = (view.get("level") or {}).get("ins") or ["A"]
        return {"action": "flip", "name": rng.choice(names)}
    if roll < 0.88:
        return {"action": "script", "step": rng.randrange(0, 4)}
    if roll < 0.94:
        return {"action": rng.choice(["hint", "hint", "answer"])}
    return {"action": "pick", "pin": rng.choice(["s:in:A", "d:out:X", "s:1.out", "d:1.A", "x"])}


def robot_request(rng, last):
    """Robot Script: pick rooms, write instructions into the lists the view offers, run the program, climb the hint ladder."""
    view = last or {}
    roll = rng.random()
    program = view.get("program") or {}
    addr = rng.choice(["main/0", "main/1", "main/0/0/0", "A/0", "B/1", "main", "x"])
    if roll < 0.03:
        return {"action": rng.choice(["open", "reset", "bogus", "undo", "clear", "load_best", "load_answer", "next", "sandbox"])}
    if roll < 0.08:
        room_ids = [r["id"] for ch in view.get("rooms", []) for r in ch.get("rooms", []) if r.get("open")]
        return {"action": "pick", "room": rng.choice(room_ids or ["x"])}
    if roll < 0.12:
        return {"action": rng.choice(["sbx_paint", "sbx_preset"]), "x": rng.randrange(0, 9), "y": rng.randrange(0, 9),
                "tile": rng.choice([".", "#", "E", "p", ">", "?"]), "name": rng.choice(["open", "maze", "workshop", "none"])}
    if roll < 0.50:
        kinds = [p["k"] for p in program.get("palette", [])] or ["F"]
        return {"action": "insert", "kind": rng.choice(kinds), "n": rng.randrange(0, 12), "cond": rng.choice(["blocked", "!part", "exit", "bad"])}
    if roll < 0.58:
        return {"action": "cursor", "list": rng.choice(["main", "A", "B", "x"]), "index": rng.randrange(0, 5)}
    if roll < 0.64:
        return {"action": "routine", "name": rng.choice(["main", "A", "B", "C"])}
    if roll < 0.74:
        return {"action": rng.choice(["remove", "move", "count", "cond"]), "at": addr, "delta": rng.choice([-1, 1]),
                "n": rng.randrange(0, 12), "cond": rng.choice(["blocked", "!part", "bad"])}
    if roll < 0.80:
        return {"action": rng.choice(["hint", "hint", "load_answer"])}
    return {"action": "run"}


def hull_request(rng, last):
    """Hull Repair: pick rooms, lay lines by touching a port and dragging over neighbouring cells, undo, clear, climb the hints."""
    view = last or {}
    roll = rng.random()
    board = view.get("board") or {}
    w, h = int(board.get("w", 5)), int(board.get("h", 5))
    if roll < 0.03:
        return {"action": rng.choice(["open", "reset", "bogus", "undo", "clear", "next", "hint", "load_answer"])}
    if roll < 0.08:
        ids = [r["id"] for deck in view.get("rooms", []) for r in deck.get("rooms", []) if r.get("open")]
        return {"action": "pick", "board": rng.choice(ids or ["x"])}
    if roll < 0.14:
        return {"action": rng.choice(["hint", "load_answer", "clear", "undo", "cell"]), "x": rng.randrange(w), "y": rng.randrange(h)}
    if roll < 0.18:
        return {"action": "clear_line", "line": rng.choice([ln["c"] for ln in board.get("lines", [])] or ["A"])}
    if roll < 0.42:
        ports = [tuple(p) for ln in board.get("lines", []) for p in (ln["src"], ln["dst"])] or [(0, 0)]
        x, y = rng.choice(ports)
        return {"action": "begin", "x": x, "y": y}
    if roll < 0.85:
        x, y, cells = rng.randrange(w), rng.randrange(h), []
        for _ in range(rng.randrange(1, 7)):
            dx, dy = rng.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])
            x, y = min(max(x + dx, 0), w - 1), min(max(y + dy, 0), h - 1)
            cells.append([x, y])
        return {"action": "move", "cells": cells}
    return {"action": "end"}


def medic_request(rng, last):
    """Station Medic: pick shifts, then scan, treat, band, robot, isolate, release, comfort and borrow, restore, climb the hints."""
    view = last or {}
    roll = rng.random()
    patients = max(1, len(view.get("patients", [])))
    cabinet = view.get("cabinet") or {}
    p = rng.randrange(patients)
    if roll < 0.03:
        return {"action": rng.choice(["open", "reset", "bogus", "next", "restore", "hint", "hint_do"])}
    if roll < 0.08:
        ids = [s["id"] for ch in view.get("rooms", []) for s in ch.get("shifts", []) if s.get("open")]
        return {"action": "pick", "shift": rng.choice(ids or ["x"])}
    if roll < 0.12:
        return {"action": rng.choice(["hint", "hint", "hint_do", "restore"])}
    if roll < 0.40:
        tests = max(1, len(cabinet.get("tests", [])))
        return {"action": "scan", "p": p, "t": rng.randrange(tests)}
    if roll < 0.70:
        tx = max(1, len(cabinet.get("tx", [])))
        return {"action": "treat", "p": p, "x": rng.randrange(tx)}
    if roll < 0.78:
        return {"action": rng.choice(["band", "robot", "isolate", "release", "comfort"]), "p": p}
    if roll < 0.84:
        return {"action": "borrow", "item": rng.randrange(max(1, len(cabinet.get("items", []))))}
    return {"action": rng.choice(["scan", "treat"]), "p": "x", "t": None, "x": 1.5}


def stranded_request(rng, last):
    """Stranded: answer on the line, rewind, jump to a scene already seen, peek at the map, climb the hint ladder."""
    view = last or {}
    roll = rng.random()
    choices = view.get("choices") or []
    if roll < 0.03:
        return {"action": rng.choice(["open", "reset", "bogus", "restart", "peek", "loose", "hint_do"])}
    if roll < 0.72 and choices:
        return {"action": "choose", "i": rng.choice(choices)["i"]}
    if roll < 0.78:
        return {"action": "choose", "i": rng.choice([-1, 99, "x"])}
    if roll < 0.86:
        return {"action": "rewind", "step": rng.randrange(0, 6)}
    if roll < 0.92:
        scenes = [n["id"] for day in view.get("map", []) for n in day.get("nodes", []) if n.get("seen")]
        return {"action": "goto", "scene": rng.choice(scenes or ["x"])}
    return {"action": rng.choice(["hint", "hint", "peek", "loose"])}


@contextlib.contextmanager
def engine_game(slug):
    """Yield (call, get_state, next_request) for an engine-style game, freshly reset."""
    with isolated_imports():
        if slug == "signal":
            conftest = load_conftest(slug)
            generator = fixture_function(conftest.g)()
            engine = next(generator)
            try:
                yield engine.call, engine.m.get_state, signal_request
            finally:
                generator.close()
        elif slug == "chronicle":
            conftest = load_conftest(slug)
            g_gen = fixture_function(conftest.g)()
            module = next(g_gen)
            try:
                module.handle_dict({"action": "boot"})
                yield (lambda req: module.handle_dict(req)), module.get_state, chronicle_request
            finally:
                g_gen.close()
        elif slug == "lexis":
            load_conftest(slug)                     # puts games/lexis on sys.path
            import game as module                    # noqa: PLC0415 -- resolved through that path
            module.handle(json.dumps({"action": "reset"}))
            yield (lambda req: json.loads(module.handle(json.dumps(req)))), module.get_state, lexis_request
        elif slug == "heist-committee":
            load_conftest(slug)                     # puts games/heist-committee on sys.path
            import game as module                    # noqa: PLC0415 -- resolved through that path
            module.handle(json.dumps({"action": "new_career", "seed": 77}))
            yield (lambda req: json.loads(module.handle(json.dumps(req)))), module.get_state, heist_request
        elif slug == "lighthouse":
            load_conftest(slug)                     # puts games/lighthouse on sys.path
            import game as module                    # noqa: PLC0415 -- resolved through that path
            module.handle(json.dumps({"action": "new_game", "seed": 77}))
            yield (lambda req: json.loads(module.handle(json.dumps(req)))), module.get_state, lighthouse_request
        elif slug == "pocket-bazaar":
            load_conftest(slug)                     # puts games/pocket-bazaar on sys.path
            import game as module                    # noqa: PLC0415 -- resolved through that path
            module.handle(json.dumps({"action": "reset"}))
            yield (lambda req: json.loads(module.handle(json.dumps(req)))), module.get_state, pocket_request
        elif slug == "dead-reckoning":
            load_conftest(slug)                     # puts games/dead-reckoning on sys.path
            import game as module                    # noqa: PLC0415 -- resolved through that path
            module.handle(json.dumps({"action": "reset"}))
            yield (lambda req: json.loads(module.handle(json.dumps(req)))), module.get_state, reckoning_request
        elif slug == "logic-gates":
            load_conftest(slug)                     # puts games/logic-gates on sys.path
            import game as module                    # noqa: PLC0415 -- resolved through that path
            module.handle(json.dumps({"action": "reset"}))
            yield (lambda req: json.loads(module.handle(json.dumps(req)))), module.get_state, gates_request
        elif slug == "robot-script":
            load_conftest(slug)                     # puts games/robot-script (and its tools) on sys.path
            import game as module                    # noqa: PLC0415 -- resolved through that path
            module.handle(json.dumps({"action": "reset"}))
            yield (lambda req: json.loads(module.handle(json.dumps(req)))), module.get_state, robot_request
        elif slug == "hull-repair":
            load_conftest(slug)                     # puts games/hull-repair (and its tools) on sys.path
            sys.modules.pop("boards", None)         # the backend's leaderboard `boards` may already be imported by another test file
            import game as module                    # noqa: PLC0415 -- resolved through that path
            module.handle(json.dumps({"action": "reset"}))
            yield (lambda req: json.loads(module.handle(json.dumps(req)))), module.get_state, hull_request
        elif slug == "station-medic":
            load_conftest(slug)                     # puts games/station-medic (and its tools) on sys.path
            import game as module                    # noqa: PLC0415 -- resolved through that path
            module.handle(json.dumps({"action": "reset"}))
            yield (lambda req: json.loads(module.handle(json.dumps(req)))), module.get_state, medic_request
        elif slug == "stranded":
            load_conftest(slug)                     # puts games/stranded on sys.path
            import game as module                    # noqa: PLC0415 -- resolved through that path
            module.handle(json.dumps({"action": "reset"}))
            yield (lambda req: json.loads(module.handle(json.dumps(req)))), module.get_state, stranded_request
        else:
            raise KeyError(slug)


# Which games the harness drives how --------------------------------------------------------------

FAKE_DOM_GAMES = ["aftermath", "canopy", "champ-de-mots", "continuum", "drift", "grid", "herd", "loop",
                  "sol", "thaw", "tide", "trade-empire"]
ENGINE_GAMES = ["signal", "chronicle", "lexis", "heist-committee", "lighthouse", "pocket-bazaar", "dead-reckoning", "logic-gates", "robot-script", "hull-repair", "station-medic", "stranded"]
ALL_GAMES = sorted(FAKE_DOM_GAMES + ENGINE_GAMES)
