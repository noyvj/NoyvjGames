"""The brief's hard rules as tests: no real medicine, no death words, no timers, no energy, no randomness, nothing that loses
progress, no audio, no leaderboards, every action visibly counted."""

import ast
import json
import re
from pathlib import Path

import game
import progress

GAME_DIR = Path(__file__).resolve().parent.parent
APP = (GAME_DIR / "app.js").read_text(encoding="utf-8")
HTML = (GAME_DIR / "index.html").read_text(encoding="utf-8")
BANNED = re.compile(r"\b(timer|countdown|stopwatch|energy|stamina|lives|hearts|streak|daily|premium|gems?|loot ?box|deck of cards|leaderboard|hurry|expires?|limited time|audio|sound effect)\b", re.IGNORECASE)
# real medicine: invented conditions only, and never dosing or instructions
MEDICAL = re.compile(r"\b(doses?|dosage|dosing|mg|ml|milligrams?|prescri\w*|antibiotics?|vaccin\w*|penicillin|insulin|aspirin|paracetamol|ibuprofen|morphine|opioids?|steroids?|chemo\w*|cancer|diabet\w*|asthma|strokes?|cardiac|heart attack|covid|coronavirus|influenza|flu|pneumonia|sepsis|viruses|virus|bacteri\w*|infections?|overdose|cpr|defibrillat\w*|surgery|surgical|symptoms?|medication|pharmac\w*|hospital|emergency room|paramedic|ambulance)\b", re.IGNORECASE)
DEATH = re.compile(r"\b(dies|died|die|dead|death|dying|fatal|kill\w*|corpse|suicide|blood|gore|murder|bleed\w*)\b", re.IGNORECASE)


def call(**req):
    return json.loads(game.handle(json.dumps(req)))


def _py_strings(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    skip = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)) and node.body and isinstance(node.body[0], ast.Expr):
            skip.add(id(node.body[0].value))
    return [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in skip]


def _all_player_text():
    out = []
    for path in GAME_DIR.glob("*.py"):
        out += [(path.name, t) for t in _py_strings(path)]
    out += [("app.js", c) for c in re.findall(r'"((?:[^"\\\n]|\\.)*)"', APP)]
    out += [("index.html", re.sub(r"<[^>]+>", " ", HTML))]
    for name in ("changelog.json", "achievements.json"):
        if (GAME_DIR / name).exists():
            out.append((name, (GAME_DIR / name).read_text(encoding="utf-8")))
    return out


def test_no_real_medicine_anywhere_the_player_reads():
    for name, text in _all_player_text():
        if name == "render.py":
            continue                                    # SVG markup, not prose
        if name == "info.py" and "not medical advice" in text.lower():
            continue                                    # the fiction notice may name what it is not
        hit = MEDICAL.search(text)
        assert not hit, "%s: %r in %r" % (name, hit and hit.group(0), text[:70])


def test_no_death_words_outside_the_about_pledge():
    for name, text in _all_player_text():
        if name == "info.py":
            continue
        hit = DEATH.search(text)
        assert not hit, "%s: %r in %r" % (name, hit and hit.group(0), text[:70])


def test_no_timer_energy_or_other_banned_words_outside_the_about_pledge():
    for name, text in _all_player_text():
        if name == "info.py":
            continue
        assert not BANNED.search(text), (name, text[:70])


def test_the_fiction_notice_is_on_the_about_page_and_the_page_description():
    import info
    assert "fiction game" in info.NOTICE and "not medical advice" in info.NOTICE
    assert "not medical advice" in HTML and 'id="info-page-notice"' in HTML


def test_the_engine_reads_no_clock_and_no_random_source():
    for path in GAME_DIR.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"^\s*(import|from)\s+(time|datetime|random|secrets)\b", text, flags=re.M), path.name
    assert "Date" not in APP and "Math.random" not in APP and "performance.now" not in APP


def test_the_page_uses_no_timers_but_the_screen_reader_announcement_and_no_audio():
    uses = re.findall(r"(setInterval|setTimeout)\(", APP)
    assert uses == ["setTimeout"]
    assert "<audio" not in HTML and "new Audio" not in APP and "AudioContext" not in APP


def test_a_shift_is_a_pure_function_of_its_actions():
    import shift
    from solver import solve_truth
    for d in list(progress.DATA.values())[:20]:
        c = game.compiled(d["id"])
        plan, st, _cost = solve_truth(c)
        a, _ = shift.replay(c, [shift.to_token(x) for x in plan])
        b, _ = shift.replay(c, [shift.to_token(x) for x in plan])
        assert a == b == st


def test_nothing_is_ever_lost_a_bad_call_keeps_the_best_seal_and_restore_is_free():
    game.game.__init__()
    call(action="treat", p=0, x=0)
    before = dict(game.game.best)
    call(action="restore")
    call(action="comfort", p=0)
    assert all(game.game.best[k] >= v for k, v in before.items())
    assert call(action="restore")["ok"]


def test_every_action_moves_a_visible_number():
    game.game.__init__()
    call(action="pick", shift="1-2")
    base = call(action="open")
    v = call(action="treat", p=0, x=0)
    assert v["tally"]["treats"] == base["tally"]["treats"] + 1
    v2 = call(action="borrow", item=0)
    assert v2["tally"]["borrows"] == v["tally"]["borrows"] + 1
    v3 = call(action="hint")
    assert v3["tally"]["hints"] == v2["tally"]["hints"] + 1
    v4 = call(action="restore")
    assert v4["tally"]["restores"] == v3["tally"]["restores"] + 1
    v5 = call(action="comfort", p=0)
    assert v5["tally"]["comforts"] == v4["tally"]["comforts"] + 1
    for ident in ("stat-shifts", "stat-clean", "stat-patients", "stat-scans", "stat-treats", "stat-restores", "stat-borrows", "stat-hints", "stat-comforts"):
        assert 'id="%s"' % ident in HTML and ident in APP


def test_no_leaderboard_or_network_calls_in_the_game_page():
    assert not re.search(r"fetch\([^)]*(http|/app/|leaderboard)", APP)
    assert "leaderboard" not in HTML.lower()


def test_the_save_holds_nothing_about_time():
    game.game.__init__()
    call(action="treat", p=0, x=0)
    assert not re.search(r"time|date|stamp|day|clock", json.dumps(game.get_state()), flags=re.I)
