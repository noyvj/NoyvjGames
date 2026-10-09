"""The brief's hard rules as tests: no timers, no energy, no randomness, nothing that loses progress, no audio, no
leaderboards, every action visibly counted."""

import ast
import json
import re
from pathlib import Path

import boards
import game
import info
import rules

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
            if hit and path.name != "info.py":                 # the About page may say what the game will not do
                raise AssertionError("%s: %r in %r" % (path.name, hit.group(0), text[:60]))
    for chunk in re.findall(r'"((?:[^"\\\n]|\\.)*)"', APP):
        assert not BANNED.search(chunk), chunk


def test_the_engine_reads_no_clock_and_no_random_source():
    for path in GAME_DIR.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"^\s*(import|from)\s+(time|datetime|random|secrets)\b", text, flags=re.M), path.name
    assert "Date" not in APP and "Math.random" not in APP and "performance.now" not in APP


def test_the_page_only_uses_one_cosmetic_timeout_and_no_interval_and_no_audio():
    uses = re.findall(r"(setInterval|setTimeout)\(", APP)
    assert uses == ["setTimeout"]                                  # the screen-reader announcement
    assert "<audio" not in HTML and "new Audio" not in APP and "AudioContext" not in APP


def test_validation_is_a_pure_function_of_board_and_layout():
    for b in boards.ALL_BOARDS:
        assert rules.status(b, b.solution) == rules.status(b, json.loads(json.dumps({c: p for c, p in b.solution.items()}))) == rules.RESTORED
        assert rules.check_layout(b, b.solution) == rules.check_layout(b, b.solution)


def test_a_wrong_drawing_never_costs_a_repair_or_the_layout_on_the_board():
    game.game.__init__()
    b = boards.ALL_BOARDS[0]
    game.game.draw.load_answer(b.solution)
    game.game._record()
    best = game.game.best[b.id]
    call(action="clear")
    call(action="begin", x=3, y=0)
    call(action="move", cells=[[2, 0], [2, 1]])
    call(action="end")
    v = call(action="open")
    assert v["totals"]["restored"] == 1 and game.game.best[b.id] == best and v["board"]["best_status"] == 2
    assert call(action="undo")["ok"] and call(action="undo")["ok"]


def test_every_action_moves_a_visible_number():
    game.game.__init__()
    base = call(action="open")
    call(action="begin", x=3, y=0)
    call(action="move", cells=[[2, 0]])
    v = call(action="end")
    assert v["tally"]["laid"] == base["tally"]["laid"] + 1
    v2 = call(action="begin", x=2, y=0)
    v2 = call(action="end")
    assert v2["tally"]["erased"] == v["tally"]["erased"] + 1
    v3 = call(action="hint")
    assert v3["tally"]["hints"] == v2["tally"]["hints"] + 1
    v4 = call(action="clear_line", line="A") if "A" in game.game.draw.paths else call(action="undo")
    assert v4["tally"]["undos"] + v4["tally"]["erased"] >= 1
    for ident in ("stat-patched", "stat-restored", "stat-laid", "stat-empty", "stat-erased", "stat-undos", "stat-hints"):
        assert 'id="%s"' % ident in HTML and ident in APP


def test_there_are_three_goals_visible_and_the_strip_is_always_on_the_page():
    game.game.__init__()
    assert len(call(action="open")["goals"]) == 3
    assert 'id="goals"' in HTML and "hidden" not in re.search(r'<section id="goals"[^>]*>', HTML).group(0)


def test_no_leaderboard_or_network_calls_in_the_game_page():
    assert "fetch(" in APP and not re.search(r"fetch\([^)]*(http|/app/|leaderboard)", APP)
    assert "leaderboard" not in HTML.lower().replace("no leaderboards", "")


def test_the_save_holds_nothing_about_time():
    game.game.__init__()
    game.game.draw.load_answer(boards.ALL_BOARDS[0].solution)
    game.game._record()
    game.game.rungs[boards.ORDER[0]] = 2
    assert not re.search(r"time|date|stamp|day|clock", json.dumps(game.get_state()), flags=re.I)


def test_the_about_page_states_the_pledge_and_no_real_world_facts():
    v = info.view()
    text = " ".join(v["pledge"]) + v["framing"]
    for needle in ("no timer", "No audio", "no leaderboards", "never"):
        assert needle in text or needle.lower() in text.lower()
    assert "invented" in v["framing"] and len(v["pledge"]) >= 5 and v["how"]
    assert call(action="open")["about"]["framing"] == v["framing"]
