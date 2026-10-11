"""The brief's hard rules as tests: no timers, no energy, no randomness, nothing that loses progress, no audio, no leaderboards, every
action visibly counted, never colour alone."""

import ast
import json
import re
from pathlib import Path

import benches
import game

GAME_DIR = Path(__file__).resolve().parent.parent
APP = (GAME_DIR / "app.js").read_text(encoding="utf-8")
HTML = (GAME_DIR / "index.html").read_text(encoding="utf-8")
CSS = (GAME_DIR / "style.css").read_text(encoding="utf-8")
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
            if path.name == "info.py":                                     # the About page may say what the game will never do
                continue
            assert not hit, "%s: %r in %r" % (path.name, hit and hit.group(0), text[:60])
    for chunk in re.findall(r'"((?:[^"\\\n]|\\.)*)"', APP):
        assert not BANNED.search(chunk), chunk
    assert not BANNED.search(re.sub(r"<[^>]+>", " ", HTML).replace("Advertisement", ""))


def test_the_engine_reads_no_clock_and_no_random_source():
    for path in GAME_DIR.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"^\s*(import|from)\s+(time|datetime|random|secrets)\b", text, flags=re.M), path.name
    assert "Date" not in APP and "Math.random" not in APP and "performance.now" not in APP


def test_the_page_only_uses_cosmetic_timeouts_and_no_interval_and_no_audio():
    uses = re.findall(r"(setInterval|setTimeout)\(", APP)
    assert set(uses) == {"setTimeout"} and len(uses) == 2             # the screen-reader announcement and the click guard after a drag
    assert "<audio" not in HTML and "new Audio" not in APP and "AudioContext" not in APP and "sfx" not in HTML.lower()


def test_no_leaderboard_or_network_calls_in_the_game_page():
    assert not re.search(r"fetch\([^)]*(http|/app/|leaderboard)", APP)
    assert "leaderboard" not in HTML.lower()


def test_nothing_can_be_lost_and_a_bench_can_always_be_started_again():
    game.game.__init__()
    for r, c, piece, state in benches.BY_ID["c1-1"].solution:
        call(action="place", r=r, c=c, piece=piece)
    assert call(action="open")["totals"]["cleared"] == 1
    call(action="clear_bench")
    v = call(action="open")
    assert v["totals"]["cleared"] == 1 and v["bench"]["status"] == "cleared"       # states only go up
    for _ in range(50):
        call(action="place", r=3, c=1, piece="mirror")
        call(action="pickup", r=3, c=1)
    assert call(action="open")["totals"]["cleared"] == 1


def test_every_action_moves_a_visible_number():
    game.game.__init__()
    base = call(action="open")["tally"]
    v = call(action="place", r=3, c=1, piece="mirror")
    assert v["tally"]["placed"] == base["placed"] + 1
    v = call(action="flip", r=3, c=1)
    assert v["tally"]["flips"] == base["flips"] + 1
    v = call(action="pickup", r=3, c=1)
    assert v["tally"]["picked"] == base["picked"] + 1
    for ident in ("stat-cleared", "stat-sensors", "stat-placed", "stat-fewest", "stat-picked", "stat-flips"):
        assert 'id="%s"' % ident in HTML and ident in APP


def test_no_state_is_told_by_colour_alone():
    """The brief: every beam kind has a dash pattern and a letter, a lit sensor a tick, a slot a dashed outline."""
    assert "stroke-dasharray" in CSS and "ml-letter" in CSS and "s-tick" in CSS and ".ml-slot" in CSS
    game.game.__init__()
    game.game._enter("c3-3")
    v = call(action="place", r=2, c=2, piece="prism")
    svg = v["bench"]["svg"]
    assert "ml-beam-S" in svg and "ml-beam-L" in svg and "s-tick" in svg and ">S</text>" in svg and ">L</text>" in svg
    assert all("lit" in s["text"] or "dark" in s["text"] for s in v["bench"]["sensors"])         # the same state, said in words


def test_there_is_no_generated_art_and_no_images_in_the_folder():
    for path in GAME_DIR.rglob("*"):
        assert path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp3", ".ogg", ".wav"}, path
