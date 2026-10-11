"""The brief's hard rules as tests: no timers, no energy, no randomness, nothing that loses progress, no audio, no
leaderboards, every action visibly counted."""

import ast
import json
import re
from pathlib import Path

import cases
import game
import lang

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
    assert "<audio" not in HTML and "new Audio" not in APP and "AudioContext" not in APP and "sfx" not in HTML.lower()


def test_the_sorters_answer_is_a_pure_function_of_the_case_and_the_item():
    for c in cases.ALL_CASES:
        dom = c.domain
        probe = dom.items[:: max(1, dom.size // 200)]
        assert [c.accepts(k) for k in probe] == [c.accepts(k) for k in probe]
        rule = lang.parse_rule(c.kind, json.loads(json.dumps(lang.rule_json(c.rule))))
        assert lang.agree(c.kind, rule, c.rule)


def test_testing_is_free_and_unlimited_and_nothing_a_test_does_can_be_lost():
    game.game.__init__()
    for n in range(100):
        v = call(action="test", item=str(n))
        assert v["ok"]
    assert call(action="open")["tally"]["tests"] == 100 - len(set(cases.BY_ID["latch"].examples))
    assert call(action="open")["totals"]["named"] == 0


def test_a_wrong_name_never_costs_anything_and_a_case_can_always_be_tried_again():
    game.game.__init__()
    c = cases.BY_ID["latch"]
    before = call(action="open")["totals"]
    wrong = lang.rule_json(lang.parse_rule("num", "ge:30"))
    for _ in range(5):
        call(action="name", rule=wrong)
    after = call(action="open")
    assert after["totals"] == before and after["case"]["status"] == "open"
    assert call(action="name", rule=lang.rule_json(c.rule))["verdict"]["kind"] == "named"


def test_every_action_moves_a_visible_number():
    game.game.__init__()
    base = call(action="open")
    v = call(action="test", item="12")
    assert v["tally"]["tests"] == base["tally"]["tests"] + 1 and v["case"]["tests"] == 1
    v = call(action="name", rule=lang.rule_json(lang.parse_rule("num", "ge:30")))
    assert v["tally"]["near"] == 1 or v["verdict"]["kind"] == "conflict"
    for ident in ("stat-named", "stat-tests", "stat-here", "stat-clean", "stat-near"):
        assert 'id="%s"' % ident in HTML and ident in APP


def test_no_leaderboard_or_network_calls_in_the_game_page():
    assert "fetch(" in APP and not re.search(r"fetch\([^)]*(http|/app/|leaderboard)", APP)
    assert "leaderboard" not in HTML.lower().replace("no leaderboards", "")


def test_the_save_holds_nothing_about_time():
    game.game.__init__()
    call(action="test", item="12")
    assert not re.search(r"time|date|stamp|day|clock", json.dumps(game.get_state()), flags=re.I)
