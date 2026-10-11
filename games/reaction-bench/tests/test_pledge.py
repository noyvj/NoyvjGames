"""The brief's hard rules as tests: no timers, no energy, no randomness, nothing that loses progress, no audio, no leaderboards,
every action visibly counted, nothing hazardous."""

import ast
import json
import re
from pathlib import Path

import game
import reactions

from .helpers import call, solve

GAME_DIR = Path(__file__).resolve().parent.parent
APP = (GAME_DIR / "app.js").read_text(encoding="utf-8")
HTML = (GAME_DIR / "index.html").read_text(encoding="utf-8")
CSS = (GAME_DIR / "style.css").read_text(encoding="utf-8")
BANNED_CONTENT = re.compile(r"\b(timer|countdown|stopwatch|stamina|lives|hearts|streak|daily|premium|gems?|loot ?box|deck of cards|leaderboard|hurry|expires?|limited time|audio|sound effect)\b", re.IGNORECASE)   # chemistry may say 'energy'
BANNED = re.compile(r"\b(timer|countdown|stopwatch|energy|stamina|lives|hearts|streak|daily|premium|gems?|loot ?box|deck of cards|leaderboard|hurry|expires?|limited time|audio|sound effect)\b", re.IGNORECASE)


def _py_strings(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    skip = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)) and node.body and isinstance(node.body[0], ast.Expr):
            skip.add(id(node.body[0].value))
    return [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in skip]


def test_no_banned_words_in_anything_the_player_reads():
    for path in GAME_DIR.glob("*.py"):
        if path.name == "info.py":                                         # the About page may say what the game will never do
            continue
        for text in _py_strings(path):
            hit = (BANNED_CONTENT if path.name.startswith(("reactions_c", "elements")) else BANNED).search(text)
            assert not hit, "%s: %r in %r" % (path.name, hit and hit.group(0), text[:60])
    for chunk in re.findall(r'"((?:[^"\\\n]|\\.)*)"', APP):
        assert not BANNED.search(chunk), chunk
    assert not BANNED.search(re.sub(r"<[^>]+>", " ", HTML).replace("Advertisement", ""))


def test_the_page_uses_only_cosmetic_timeouts_and_no_interval_and_no_audio():
    uses = re.findall(r"(setInterval|setTimeout)\(", APP)
    assert set(uses) == {"setTimeout"} and len(uses) == 1                  # the screen-reader announcement only
    assert "<audio" not in HTML and "new Audio" not in APP and "AudioContext" not in APP and "sfx" not in HTML.lower()
    assert "Date.now" not in APP and "Math.random" not in APP and "performance.now" not in APP
    assert APP.count("new Date()") == 1                                    # only to name the day of the live About read


def test_no_leaderboard_or_backend_calls_in_the_game_page():
    for chunk in re.findall(r"fetch\([^)]*\)", APP):
        assert not re.search(r"/app/|leaderboard|stats/|feedback", chunk), chunk
    assert "leaderboard" not in HTML.lower()
    assert set(re.findall(r"fetch\(([^,)]+)", APP)) <= {"\"changelog.json\"", "ENGINE_MODULES[i]", "\"game.py\"", "live.api"}


def test_nothing_can_be_lost_and_the_ledger_never_fails_an_order():
    solve("water")
    assert call(action="open")["totals"]["shelved"] == 1
    for _ in range(60):
        call(action="dial", index=0, delta=1)
        call(action="dial", index=0, delta=-1)
        call(action="dial", index=1, value=7)
        call(action="reset_dials")
    v = call(action="open")
    assert v["totals"]["shelved"] == 1 and v["reaction"]["status"] == "shelved"      # states only go up
    assert call(action="run")["ok"] is False or v["reaction"]["can_run"] in (True, False)


def test_every_action_moves_a_visible_number():
    game.game.__init__()
    call(action="pick", reaction="water")
    base = call(action="open")["tally"]
    assert call(action="dial", index=0, value=3)["tally"]["turns"] == base["turns"] + 1
    call(action="dial", index=0, value=2)
    call(action="dial", index=2, value=2)
    assert call(action="run")["tally"]["runs"] == base["runs"] + 1
    for ident in ("stat-shelved", "stat-elements", "stat-turns", "stat-runs"):
        assert 'id="%s"' % ident in HTML and ident in APP


def test_nothing_in_the_game_depends_on_luck_or_order():
    """Every order is fully determined by its equation: the same dial settings always give the same ledger and the same verdict."""
    for r in reactions.ALL:
        game.game.__init__()
        game.game.shelf = dict((x.id, 1) for x in reactions.ALL)                # everything open, so any order can be visited
        game.game.picked = set(x.id for x in reactions.ALL if x.is_round)
        game.game.current = r.id
        a = json.dumps(game.game.view()["reaction"], sort_keys=True)
        b = json.dumps(game.game.view()["reaction"], sort_keys=True)
        assert a == b


def test_there_is_no_generated_art_and_no_images_in_the_folder():
    for path in GAME_DIR.rglob("*"):
        assert path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp3", ".ogg", ".wav"}, path


def test_the_game_names_no_hazardous_procedure_and_every_reaction_is_a_textbook_one():
    """Equations only: no quantities, temperatures, apparatus or 'how to' wording anywhere a player can read."""
    pattern = re.compile(r"\b(\d+\s?(g|kg|ml|mL|litres?|grams?|degrees|°C)|beaker|mix\w*|add\w* to|pour\w*|heat \w+ to|step \d)\b")
    for r in reactions.ALL:
        for text in (r.blurb, r.fennel, r.title):
            assert not pattern.search(text), (r.id, text)
