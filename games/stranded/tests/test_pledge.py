"""The brief's hard rules as tests: no on-screen death, no timers or energy, no clocks or randomness, nothing that loses
progress, no audio, no leaderboards, every action visibly counted."""

import ast
import json
import re
from pathlib import Path

import game
import lore
import story

GAME_DIR = Path(__file__).resolve().parent.parent
BANNED = re.compile(r"\b(timer|timers|countdown|stopwatch|clock|clocks|energy|stamina|lives|hearts|streak|daily|premium|gems?|loot ?box|deck of cards|leaderboard|hurry|expires?|expired|deadline|limited time|audio|sound effect|ticking)\b", re.IGNORECASE)
DEATH = re.compile(r"\b(dies|died|die|dead|death|dying|fatal|kill\w*|corpse|suicide|blood|gore|murder|bleed\w*|lethal|perish\w*|doomed|grave|funeral)\b", re.IGNORECASE)
SELF_HARM = re.compile(r"\b(self-harm|hopeless|worthless|hate myself|end it all|give up on living)\b", re.IGNORECASE)


def call(**req):
    return json.loads(game.handle(json.dumps(req)))


def _py_strings(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    skip = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)) and node.body and isinstance(node.body[0], ast.Expr):
            skip.add(id(node.body[0].value))
    return [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in skip]


def _story_text():
    out = []
    for scene in story.SCENES.values():
        out.append((scene["id"], scene["title"]))
        out += [(scene["id"], t) for _c, t in scene["lines"]]
        for c in scene["choices"]:
            out.append((scene["id"], c["text"]))
            out += [(scene["id"], t) for _c, t in c["reply"]]
    for day, (title, narrator) in lore.DAYS.items():
        out += [("day%d" % day, title), ("day%d" % day, narrator)]
    for cid, _k, title, text, hint in lore.COLLECT:
        out += [(cid, title), (cid, text), (cid, hint)]
    return out


def _player_text():
    out = list(_story_text())
    for name in ("achievements.py", "game.py", "explore.py", "walker.py"):
        out += [(name, t) for t in _py_strings(GAME_DIR / name)]
    for name in ("changelog.json", "achievements.json"):
        if (GAME_DIR / name).exists():
            out.append((name, (GAME_DIR / name).read_text(encoding="utf-8")))
    return out


def test_no_on_screen_death_anywhere_the_player_reads():
    for name, text in _player_text():
        hit = DEATH.search(text)
        assert not hit, "%s: %r in %r" % (name, hit and hit.group(0), text[:70])
        assert not SELF_HARM.search(text), (name, text[:70])


def test_no_timer_energy_clock_or_other_banned_words_in_the_story_or_the_game_text():
    for name, text in _player_text():
        assert not BANNED.search(text), (name, text[:70])


def test_the_about_page_may_name_what_it_refuses_but_nothing_else_does():
    import info
    text = " ".join(info.PLEDGE) + info.NOTICE
    assert "no timer" in text.lower() and "Nobody dies on screen" in text and "Stranded is fiction" in info.NOTICE
    for fact in info.FACTS:
        assert fact["source"]["url"].startswith("https://") and fact["source"]["date_read"] == "2026-10-10" and fact["source"]["publisher"]


def test_the_engine_reads_no_clock_and_no_random_source():
    for path in GAME_DIR.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        if path.stem == "game":
            text = text.replace("        import js\n", "")           # the one allowed import: the redraw hook
        assert not re.search(r"^\s*(import|from)\s+(time|datetime|random|secrets|js)\b", text, flags=re.M), path.name
        assert "Date" not in text and "Math.random" not in text


def test_every_ending_is_warm_or_bittersweet_and_nobody_is_lost():
    for eid, sid, _title in story.ENDINGS:
        text = " ".join(t for _c, t in story.SCENES[sid]["lines"])
        assert "Harbour" in text and len(story.SCENES[sid]["lines"]) >= 4, eid
        assert not DEATH.search(text), eid


def test_a_poor_choice_never_ends_anything_and_the_stats_floor_at_zero():
    call(action="reset")
    v = None
    for ch in "111":
        v = call(action="choose", i=int(ch))
    assert v["ok"] and all(s["value"] >= 0 for s in v["stats"])


def test_nothing_is_ever_lost_rewind_keeps_everything_and_reset_is_the_only_erase():
    call(action="reset")
    for ch in "0000":
        call(action="choose", i=int(ch))
    before = call(action="open")["progress"]
    call(action="rewind", step=1)
    assert call(action="open")["progress"] == before


def test_every_action_moves_a_visible_number():
    call(action="reset")
    a = call(action="open")["tally"]["sent"]
    v = call(action="choose", i=0)
    assert v["tally"]["sent"] == a + 1 and v["progress"]["tried"][0] == 1
    v = call(action="rewind", step=0)
    assert v["tally"]["rewinds"] == 1
    v = call(action="hint")
    assert v["tally"]["hints"] == 1
    call(action="choose", i=1)
    call(action="restart")
    call(action="choose", i=0)
    call(action="restart")
    v = call(action="peek")
    assert v["tally"]["peeks"] == 1
    v = call(action="goto", scene="d1b")
    assert v["tally"]["jumps"] == 1


def test_the_save_holds_nothing_about_time():
    call(action="reset")
    call(action="choose", i=0)
    assert not re.search(r"time|date|stamp|clock|hour|expire", json.dumps(game.get_state()), flags=re.I)


def test_the_page_scripts_use_no_clock_no_random_no_audio_and_one_timeout_for_the_screen_reader():
    app = (GAME_DIR / "app.js").read_text(encoding="utf-8")
    html = (GAME_DIR / "index.html").read_text(encoding="utf-8")
    assert re.findall(r"(setInterval|setTimeout)\(", app) == ["setTimeout"]
    assert "Date" not in app and "Math.random" not in app and "performance.now" not in app and "requestAnimationFrame" not in app
    for name in ("settings.js", "pc.js"):
        text = (GAME_DIR / name).read_text(encoding="utf-8")
        assert not re.search(r"setInterval|setTimeout|Math\.random|Date\b", text), name
    assert "<audio" not in html and "new Audio" not in app and "AudioContext" not in app
    assert not re.search(r"fetch\([^)]*(http|/app/|leaderboard)", app) and "leaderboard" not in html.lower()
