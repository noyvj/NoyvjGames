"""The brief's hard rules as tests: no timers, no energy, no randomness, nothing that loses progress, no audio, no
leaderboards, every action visibly counted."""

import ast
import json
import re
from pathlib import Path

import game
import rooms

GAME_DIR = Path(__file__).resolve().parent.parent
APP = (GAME_DIR / "app.js").read_text(encoding="utf-8")
HTML = (GAME_DIR / "index.html").read_text(encoding="utf-8")
BANNED = re.compile(r"\b(timer|countdown|stopwatch|energy|stamina|lives|hearts|streak|daily|premium|gems?|loot ?box|deck of cards|leaderboard|hurry|expires?|limited time|audio|sound effect)\b", re.IGNORECASE)


def call(**req):
    return json.loads(game.handle(json.dumps(req)))


def _py_strings(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    skip = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)) and node.body and isinstance(node.body[0], ast.Expr):
            skip.add(id(node.body[0].value))
    return [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in skip]


def test_no_banned_words_in_anything_the_player_reads():
    for path in GAME_DIR.glob("*.py"):
        for text in _py_strings(path):
            hit = BANNED.search(text)
            # the About page may say what the game will not do; only the pledge list may use these words
            if hit and path.name != "info.py":
                raise AssertionError("%s: %r in %r" % (path.name, hit.group(0), text[:60]))
    for chunk in re.findall(r'"((?:[^"\\\n]|\\.)*)"', APP):
        assert not BANNED.search(chunk), chunk


def test_the_engine_reads_no_clock_and_no_random_source():
    for path in GAME_DIR.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"^\s*(import|from)\s+(time|datetime|random|secrets)\b", text, flags=re.M), path.name
    assert "Date" not in APP and "Math.random" not in APP and "performance.now" not in APP


def test_the_page_only_uses_timers_for_cosmetic_playback():
    uses = re.findall(r"(setInterval|setTimeout)\(", APP)
    assert uses.count("setInterval") == 2 and uses.count("setTimeout") == 1      # playback steps and the screen-reader announcement
    assert "<audio" not in HTML and "new Audio" not in APP and "AudioContext" not in APP


def test_a_run_is_a_pure_function_of_room_and_list():
    import run
    for r in rooms.ALL_ROOMS:
        a, b = run.run(r.layout, r.ref), run.run(r.layout, r.ref)
        assert a.frames == b.frames and a.status == b.status == "cleared"


def test_a_stopped_run_keeps_the_list_and_never_costs_a_medal():
    game.game.__init__()
    rid = "first-delivery"
    game.game._enter(rid)
    game.game.ed.load(rooms.BY_ID[rid].ref)
    call(action="run")
    before = game.game.best[rid]
    game.game.ed.clear()
    for _ in range(12):
        call(action="insert", kind="F")
    text = json.dumps(game.game.ed.prog)
    v = call(action="run")
    assert v["run"]["status"] == "halt"
    assert json.dumps(game.game.ed.prog) == text and game.game.best[rid] == before
    assert v["totals"]["gold"] == 1


def test_medals_and_progress_only_ever_go_up():
    game.game.__init__()
    rid = "long-hall"
    game.game._enter(rid)
    game.game.ed.load(rooms.BY_ID[rid].ref)
    call(action="run")
    gold = game.game.best[rid]["n"]
    game.game.ed.clear()
    for k in "FFFFFFFF":
        call(action="insert", kind="F")
    call(action="run")
    assert game.game.best[rid]["n"] == gold


def test_every_action_moves_a_visible_number():
    game.game.__init__()
    base = call(action="open")
    v = call(action="insert", kind="F")
    assert v["tally"]["written"] == base["tally"]["written"] + 1
    v2 = call(action="run")
    assert v2["tally"]["runs"] == v["tally"]["runs"] + 1
    v3 = call(action="hint")
    assert v3["tally"]["hints"] == v2["tally"]["hints"] + 1
    for ident in ("stat-rooms", "stat-gold", "stat-parts", "stat-runs", "stat-written", "stat-hints", "stat-halts", "stat-sbx-runs", "stat-sbx-tiles"):
        assert 'id="%s"' % ident in HTML and ident in APP


def test_there_are_exactly_three_goals_visible_and_the_strip_is_always_on_the_page():
    game.game.__init__()
    assert len(call(action="open")["goals"]) == 3
    assert 'id="goals"' in HTML and "hidden" not in re.search(r'<section id="goals"[^>]*>', HTML).group(0)


def test_no_leaderboard_or_network_calls_in_the_game_page():
    assert "fetch(" in APP and not re.search(r"fetch\([^)]*(http|/app/|leaderboard)", APP)
    assert "leaderboard" not in HTML.lower().replace("no leaderboards", "")


def test_the_save_holds_nothing_about_time():
    game.game.__init__()
    game.game._enter("wake-up")
    game.game.ed.load(rooms.BY_ID["wake-up"].ref)
    call(action="run")
    text = json.dumps(game.get_state())
    assert not re.search(r"time|date|stamp|day|clock", text, flags=re.I)
